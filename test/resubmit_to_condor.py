"""
Resubmit failed CRAB jobs to condor.
"""

import subprocess
import importlib
import argparse
import os
import sys
import time


def get_args():
    parser = argparse.ArgumentParser(description="Resubmit failed CRAB jobs to condor")
    parser.add_argument(
        "--dataset",
        type=str,
        help="Name of dataset to resubmit",
        default="DYJetsToMuMu_M-50_massWgtFix_TuneCP5_13TeV-powhegMiNNLO-pythia8-photos",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input python file that contains the dict with the files to process",
        default="files_for_condor.py",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output base directory",
        default="/store/group/lpcsuep/Muon_counting_search/SUEPNano_UL18_Nov2024/"
        "DYJetsToMuMu_M-50_massWgtFix_TuneCP5_13TeV-powhegMiNNLO-pythia8-photos/"
        "DYJetsToMuMu_M-50_massWgtFix_TuneCP5_13TeV-powhegMiNNLO-pythia8-photos/241119_005128/0000",
    )
    parser.add_argument(
        "--redirector",
        type=str,
        help="xrootd redirector to use",
        default="root://cmseos.fnal.gov/",
    )
    parser.add_argument(
        "--max-split",
        action="store_true",
        help="Submit one job per input file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information",
    )
    return parser.parse_args()


def create_condor_script(args, job, work_dir, files, cmssw_version):
    """Create a condor submission script and executable for this dataset"""
    work_dir_job = "{}/condor_{}_{}".format(work_dir, args.dataset, job)
    if not os.path.exists(work_dir_job):
        os.makedirs(work_dir_job)

    # Write the input files to a text file
    input_file = os.path.join(work_dir_job, "input_files_{}.txt".format(job))
    with open(input_file, "w") as f:
        for file in files:
            f.write("{}\n".format(file))

    # Write condor executino script
    exec_script = os.path.join(work_dir_job, "run_cmssw.sh")
    with open(exec_script, "w") as f:
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
echo "Output directory: $2"
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
cp ../NANO_mc_cfg.py {cmssw_version}/src
cp ../input_files_$1.txt {cmssw_version}/src
cd {cmssw_version}/src
scramv1 b ProjectRename
eval $(scramv1 runtime -sh) # cmsenv is an alias not on the workers
ls -lh 

# Run the CMSSW job

cmsRun NANO_mc_cfg.py inputFiles=input_files_$1.txt outputFile=nano_skim_$1.root

# Check if job was successful
if [ $? -ne 0 ]; then
    echo "CMSSW job failed!"
    exit 1
fi

# Copy output
xrdcp -f nano_skim_$1.root $2/nano_skim_$1.root
if [ $? -ne 0 ]; then
    echo "Copy to EOS failed!"
    exit 1
fi

echo "Cleaning up"
rm nano_skim_$1.root
echo "Job completed successfully"
""".format(
                job=job,
                cmssw_version=cmssw_version,
            )
        )
    os.chmod(exec_script, 0o755)

    # Get CMSSW tarball name
    cmssw_tarball = "{}.tar.gz".format(cmssw_version)

    # Create the condor submit file
    submit_file = os.path.join(work_dir_job, "submit.jdl")
    with open(submit_file, "w") as f:
        f.write(
            """# Condor submit file for merging files
universe = vanilla
executable = {executable}
arguments = {job} {output_dir}
output = {work_dir_job}/$(ClusterId).$(ProcId).stdout
error = {work_dir_job}/$(ClusterId).$(ProcId).stderr
log = {work_dir_job}/$(ClusterId).$(ProcId).log

# Transfer files
transfer_input_files = {work_dir_job}/input_files_{job}.txt,NANO_mc_cfg.py,{cmssw_tarball}
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
# Periodic hold conditions
periodic_hold = (\\
    ( JobUniverse == 5 && JobStatus == 2 && CurrentTime - EnteredCurrentStatus > $(ONE_DAY) * 1.75 ) || \\
    ( JobRunCount > 8 ) || \\
    ( JobStatus == 5 && CurrentTime - EnteredCurrentStatus > $(ONE_DAY) * 6 ) || \\
    ( DiskUsage > 38000000 ) || \\
    ( ifthenelse(ResidentSetSize isnt undefined, ResidentSetSize > RequestMemory * 975, false) ) )

# Explain periodic hold
periodic_hold_reason = strcat("Job held by PERIODIC_HOLD (code ", HoldReasonCode, ") due to ", \\
    ifThenElse(( JobUniverse == 5 && JobStatus == 2 && CurrentTime - EnteredCurrentStatus > $(ONE_DAY) * 1.75 ), "runtime longer than 1.75 days", \\
    ifThenElse(( JobRunCount > 8 ), "JobRunCount greater than 8", \\
    ifThenElse(( JobStatus == 5 && CurrentTime - EnteredCurrentStatus > $(ONE_DAY) * 6 ), "hold time longer than 6 days", \\
    ifThenElse(( DiskUsage > 38000000 ), "disk usage greater than 38GB", \\
                strcat("memory usage ",ResidentSetSize," greater than requested ",RequestMemory*1000))))), ".")

queue 1
""".format(
                executable=exec_script,
                work_dir_job=work_dir_job,
                job=job,
                cmssw_tarball=cmssw_tarball,
                output_dir=args.redirector + args.output,
            )
        )

    return submit_file


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
        "{version} --exclude=tmp --exclude=*.tar.gz --exclude=*.root"
    ).format(cwd=cwd, tarball=tarball, version=cmssw_version)
    subprocess.check_call(cmd.split())
    os.chdir(cwd)
    print(
        "Created CMSSW tarball: {} of size {} MB".format(
            tarball, round(os.path.getsize(tarball) / 1000.0**2, 1)
        )
    )
    return tarball, cmssw_version


def split_input_files(input):
    """Split input files into individual jobs"""
    output = {}
    for key in input:
        for i, item in enumerate(input[key]):
            output["{}_{}".format(key, i)] = [item]

    return output


if __name__ == "__main__":
    args = get_args()

    # Import the input file
    input = importlib.import_module(args.input.replace(".py", ""))

    # Create CMSSW tarball
    cmssw_tarball, cmssw_version = create_cmssw_tarball()

    input_files = input.files_for_condor
    if args.max_split:
        input_files = split_input_files(input.files_for_condor)

    print("Found {} jobs to resubmit:".format(len(input_files)))

    # Create a working directory for condor files
    work_dir = "condor_resubmit_{}".format(time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(work_dir)

    submit_files = []
    for job in input_files:
        print("  {} ({} files)".format(job, len(input_files[job])))

        # Create condor submission for this dataset
        submit_file = create_condor_script(
            args,
            job,
            work_dir,
            input_files[job],
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
