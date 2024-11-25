"""
Run this script to merge files from different directories on EOS.
Produce a JSON file with the merged files.
"""

import subprocess
import argparse
import os
import time
import sys


def eos_ls(args, directory):
    """List contents of a directory on EOS"""
    max_retries = 3
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            command = "source ~/.bash_profile 2>/dev/null; eos {} ls {}".format(
                args.redirector, directory
            )
            result = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                executable="/bin/bash",
            )
            out, err = result.communicate()
            # If error occurred or output is empty, try again
            if err or not out:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return []
            return [x for x in out.decode("utf-8").strip().split("\n") if x]
        except:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return []
    return []


def get_datasets_and_files(args):
    """
    Get all datasets and their ROOT files in a single pass.
    Returns a dictionary {dataset_dir: [root_files]}
    """
    print("Scanning input directory: {}".format(args.input))
    dataset_files = {}
    top_contents = eos_ls(args, args.input)
    print("Found {} potential dataset directories".format(len(top_contents)))

    # Process each potential dataset directory
    for i, dataset in enumerate(top_contents, 1):
        print("\nProcessing directory {}/{}".format(i, len(top_contents)))
        dataset_path = os.path.join(args.input, dataset)
        files = get_root_files_recursive(args, dataset_path)
        if files:  # Only include directories that have ROOT files
            dataset_files[dataset_path] = files
            print("  -> Found {} ROOT files".format(len(files)))
        else:
            print("  -> No ROOT files found")

    return dataset_files


def get_root_files_recursive(args, directory):
    """Recursively get all .root files from a directory"""
    if args.verbose:
        print("  Scanning {}".format(directory))

    # Skip if this is a log directory
    if "/log" in directory:
        return []

    result = []
    contents = eos_ls(args, directory)

    for item in contents:
        if not item:  # Skip empty strings
            continue

        full_path = os.path.join(directory, item)

        # Skip log directories
        if item == "log":
            continue

        if item.endswith(".root"):
            result.append(full_path)
            if args.verbose:
                print("    Found ROOT file: {}".format(item))
        else:
            # Try to list the item - if it succeeds and returns content, it's a directory
            subdir_contents = eos_ls(args, full_path)
            if subdir_contents:  # Only recurse if we got valid contents
                result.extend(get_root_files_recursive(args, full_path))

    return result


def eos_file_size(args, file_path):
    """Get the size of a file on EOS in bytes"""
    command = "eos {} stat {}".format(args.redirector, file_path)
    result = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, executable="/bin/bash"
    )
    out, err = result.communicate()
    next_one = False
    for item in out.decode("utf-8").strip().split(" "):
        if next_one:
            return int(item)
        if item == "Size:":
            next_one = True


def get_args():
    parser = argparse.ArgumentParser(
        description="Merge files from different directories recursively"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input base directory",
        default="/store/group/lpcsuep/Muon_counting_search/SUEPNano_UL18_Nov2024",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output base directory",
        default="/store/group/lpcsuep/Muon_counting_search/SUEPNano_UL18_Nov2024_merged",
    )
    parser.add_argument(
        "--max_size", type=int, default=2, help="Maximum size of output files in GB"
    )
    parser.add_argument(
        "--redirector",
        type=str,
        default="root://cmseos.fnal.gov/",
        help="EOS redirector for the input files",
    )
    parser.add_argument(
        "--memory",
        type=int,
        default=4000,
        help="Memory request for condor jobs in MB",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information",
    )
    return parser.parse_args()


def create_condor_script(args, dataset_dir, files, max_size, work_dir, cmssw_version):
    """Create a condor submission script and executable for this dataset"""
    dataset_name = os.path.basename(dataset_dir)

    work_dir_dataset = "{}/condor_{}".format(work_dir, dataset_name)
    if not os.path.exists(work_dir_dataset):
        os.makedirs(work_dir_dataset)

    # Write the split file lists
    n_jobs = split_files_for_jobs(files, max_size, args, work_dir_dataset)

    # Write merge script
    merge_script = os.path.join(work_dir_dataset, "merge.sh")
    with open(merge_script, "w") as f:
        f.write(
            """#!/bin/bash
# Date/time of start of job
echo "Starting job on " $(date)
# Condor job is running on this node 
echo "Running on: $(uname -a)" 
# Operating System on that node
echo "System software: $(cat /etc/redhat-release)" 
source /cvmfs/cms.cern.ch/cmsset_default.sh
echo "Running merge for job $1"
echo "Contents of working directory:"
ls -la

# Move to a tmp dir to avoid conflicts
tmp_dir=$(mktemp -d -p .)
cd $tmp_dir
tar -xf ../{cmssw_version}.tar.gz
rm ../{cmssw_version}.tar.gz
export SCRAM_ARCH=slc7_amd64_gcc700
if [ ! -d {cmssw_version}/src ]; then
    mkdir -p {cmssw_version}/src
fi
mv ../files_$1.txt ../haddnano.py {cmssw_version}/src
cd {cmssw_version}/src
eval $(scramv1 runtime -sh) # cmsenv is an alias not on the workers

# If there is only one file, just copy it
if [ $(wc -l < files_$1.txt) -eq 1 ]; then
    xrdcp -f $(cat files_$1.txt) {redirector}{output_dir}/merged_$1.root
    if [ $? -ne 0 ]; then
        echo "Copy to EOS failed!"
        exit 1
    fi
    echo "Cleaning up"
    echo "Job completed successfully"
    exit 0
fi

# Do the merge
python haddnano.py merged_$1.root $(cat files_$1.txt)

# Check if merge was successful
if [ $? -ne 0 ]; then
    echo "Merge failed!"
    exit 1
fi

# Copy output
xrdcp -f merged_$1.root {redirector}{output_dir}/merged_$1.root
if [ $? -ne 0 ]; then
    echo "Copy to EOS failed!"
    exit 1
fi

echo "Cleaning up"
rm merged_$1.root
echo "Job completed successfully"
""".format(
                redirector=args.redirector,
                output_dir=os.path.join(args.output, dataset_name),
                cmssw_version=cmssw_version,
            )
        )
    os.chmod(merge_script, 0o755)

    # Get CMSSW tarball name
    cmssw_tarball = "{}.tar.gz".format(cmssw_version)

    # Create the condor submit file
    submit_file = os.path.join(work_dir_dataset, "submit.jdl")
    with open(submit_file, "w") as f:
        f.write(
            """# Condor submit file for merging files
universe = vanilla
executable = {executable}
arguments = $(ProcId)
output = {work_dir_dataset}/$(ClusterId).$(ProcId).stdout
error = {work_dir_dataset}/$(ClusterId).$(ProcId).stderr
log = {work_dir_dataset}/$(ClusterId).$(ProcId).log

# Transfer files
transfer_input_files = {work_dir_dataset}/files_$(ProcId).txt,haddnano.py,{cmssw_tarball}
should_transfer_files = YES
when_to_transfer_output = ON_EXIT

# Requirements and resources
x509userproxy = $ENV(X509_USER_PROXY)
request_memory = 4000
+REQUIRED_OS = "rhel7"
+DesiredOS = REQUIRED_OS

# Exit and hold
notification = Never
want_graceful_removal = true
on_exit_remove = (ExitBySignal == False) && (ExitCode == 0)
on_exit_hold = ( (ExitBySignal == True) || (ExitCode != 0) )
on_exit_hold_reason = strcat("Job held by ON_EXIT_HOLD due to ",\\
	ifThenElse((ExitBySignal == True), "exit by signal", \\
strcat("exit code ",ExitCode)), ".")

ONE_DAY = 86400
periodic_hold = (\\
    ( JobUniverse == 5 && JobStatus == 2 && CurrentTime - EnteredCurrentStatus > $(ONE_DAY) * 1.75 ) || \\
    ( JobRunCount > 8 ) || \\
    ( JobStatus == 5 && CurrentTime - EnteredCurrentStatus > $(ONE_DAY) * 6 ) || \\
    ( DiskUsage > 38000000 ) || \\
    ( ifthenelse(ResidentSetSize isnt undefined, ResidentSetSize > RequestMemory * 950, false) ) )
periodic_hold_reason = strcat("Job held by PERIODIC_HOLD due to ", \\
    ifThenElse(( JobUniverse == 5 && JobStatus == 2 && CurrentTime - EnteredCurrentStatus > $(ONE_DAY) * 1.75 ), "runtime longer than 1.75 days", \\
    ifThenElse(( JobRunCount > 8 ), "JobRunCount greater than 8", \\
    ifThenElse(( JobStatus == 5 && CurrentTime - EnteredCurrentStatus > $(ONE_DAY) * 6 ), "hold time longer than 6 days", \\
    ifThenElse(( DiskUsage > 38000000 ), "disk usage greater than 38GB", \\
                strcat("memory usage ",ResidentSetSize," greater than requested ",RequestMemory*1000))))), ".")

queue {n_jobs}
""".format(
                executable=merge_script,
                work_dir_dataset=work_dir_dataset,
                n_jobs=n_jobs,
                cmssw_tarball=cmssw_tarball,
            )
        )

    return submit_file


def split_files_for_jobs(files, max_size, args, work_dir_job):
    """Split files into groups based on size"""
    groups = []
    current_group = []
    current_size = 0

    for f in files:
        size = eos_file_size(args, f)
        if current_size + size > max_size and current_group:
            groups.append(current_group)
            current_group = []
            current_size = 0
        current_group.append(f)
        current_size += size

    if current_group:
        groups.append(current_group)

    # Write each group to a separate file
    for i, group in enumerate(groups):
        output_file = os.path.join(work_dir_job, "files_{}.txt".format(i))
        with open(output_file, "w") as f:
            for file_path in group:
                f.write(args.redirector + file_path + "\n")

    return len(groups)


def create_cmssw_tarball():
    """Create a tarball of the current CMSSW environment"""
    if not "CMSSW_BASE" in os.environ:
        print("Please run cmsenv in your CMSSW environment first")
        sys.exit(1)

    cmssw_base = os.environ["CMSSW_BASE"]
    cmssw_version = os.path.basename(cmssw_base)
    tarball = "{}.tar.gz".format(cmssw_version)

    # Check if tarball already exists
    if os.path.exists(tarball):
        os.remove(tarball)

    print("Creating CMSSW tarball...")
    # Get the relative path from where we are to CMSSW_BASE
    cwd = os.getcwd()
    os.chdir(os.path.dirname(cmssw_base))

    # Create the tarball excluding unnecessary directories
    cmd = (
        "tar --exclude-caches-all --exclude-vcs -zcf {cwd}/{version}.tar.gz -C {version}/.. "
        "{version} --exclude=src --exclude=tmp --exclude=*.tar.gz --exclude=*.root"
    ).format(cwd=cwd, tarball=tarball, version=cmssw_version)
    subprocess.check_call(cmd.split())
    os.chdir(cwd)
    print(
        "Created CMSSW tarball: {} of size {} MB".format(
            tarball, round(os.path.getsize(tarball) / 1000.0**2, 1)
        )
    )
    return tarball, cmssw_version


if __name__ == "__main__":
    all_data = {}
    args = get_args()

    # Check for haddnano.py
    if not os.path.exists("haddnano.py"):
        print("Please make sure haddnano.py is in the current directory")
        sys.exit(1)

    # Create CMSSW tarball
    cmssw_tarball, cmssw_version = create_cmssw_tarball()

    # Get all datasets and their files in one pass
    dataset_files = get_datasets_and_files(args)

    print("Found {} datasets to process:".format(len(dataset_files)))
    submit_files = []

    # Create a working directory for condor files
    work_dir = "condor_merge_{}".format(time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(work_dir)

    for dataset_dir in sorted(dataset_files.keys()):
        print("  {} ({} files)".format(dataset_dir, len(dataset_files[dataset_dir])))

        # Create condor submission for this dataset
        submit_file = create_condor_script(
            args,
            dataset_dir,
            dataset_files[dataset_dir],
            args.max_size * 1000**3,
            work_dir,
            cmssw_version,
        )
        submit_files.append(submit_file)

    # Create a master submit script
    submit_script = os.path.join(work_dir, "submit_all.sh")
    with open(submit_script, "w") as f:
        f.write("#!/bin/bash\n")
        for submit_file in submit_files:
            f.write("condor_submit {}\n".format(submit_file))
    os.chmod(submit_script, 0o755)

    print("\nCreated condor submission files.")
    print("To submit all jobs, run: ./{}".format(submit_script))
    print(
        "Or submit individual datasets with: condor_submit {}/condor_*/submit.cmd".format(
            work_dir
        )
    )