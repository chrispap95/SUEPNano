import os
import argparse
from multiprocessing import Pool
from contextlib import closing
import subprocess
import glob

from tqdm import tqdm  # type: ignore [import]
import ROOT  # type: ignore [import]


def get_args():
    parser = argparse.ArgumentParser(usage="%prog [options]")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Accepts either: 1) a path to a single input root file, "
        "2) text file containting a list of paths to root files, or "
        "3) directory containign root files to be split.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Destination for the final output files. E.g., ",
    )
    parser.add_argument(
        "--hadd",
        action="store_true",
        default=False,
        help="If activated, run hadd over split chunks to get merged .root files.",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        help="How many cores to take (default = 1, sequential running).",
    )
    parser.add_argument(
        "-D",
        "--drop",
        default=["GenModel_*"],
        action="append",
        help="Branches to drop. Default is to drop the 'GenModel' ones.",
    )
    parser.add_argument(
        "-K",
        "--keep",
        default=[],
        action="append",
        help="Branches to keep. Default is all.",
    )
    return parser.parse_args()


class RootFileManager(object):
    """Context manager for ROOT files in Python 2"""

    def __init__(self, filename, mode="read"):
        self.filename = filename
        self.mode = mode
        self.root_file = None

    def __enter__(self):
        self.root_file = ROOT.TFile.Open(self.filename, self.mode)
        if not self.root_file or self.root_file.IsZombie():
            raise RuntimeError("Failed to open file: %s" % self.filename)
        return self.root_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.root_file:
            self.root_file.Close()


def get_input_files(input):
    input_files = []
    if input.endswith(".root"):
        input_files = [input]
    elif os.path.isfile(input):
        with open(input, "r") as f:
            input_files = [x.strip() for x in f.readlines()]
    else:
        input_files = glob.glob("{}/*.root".format(input))
    return input_files


def splitfile(inputs):
    fname, options = inputs
    all_scan_points = {}
    if not os.path.exists(options.output):
        os.system("mkdir -p " + options.output)

    # Open the file and get the tree
    with RootFileManager(fname) as f_in:
        tree = f_in.Events
        n_events = tree.GetEntries()
        print("Total events in %s: %d" % (fname, n_events))

        # Speed up by only using useful branches
        tree.SetBranchStatus("*", 0)
        tree.SetBranchStatus("GenModel*", 1)

        # Get the list of scan points
        list_branches = [key.GetName() for key in tree.GetListOfBranches()]
        for branch in list_branches:
            if "GenModel" in branch:
                name = branch.replace("GenModel_", "")
                all_scan_points[name] = ROOT.TEventList(name, name)

        # Now we fill up the TEventList
        for n_event in tqdm(xrange(n_events)):  # type: ignore [name-defined]
            tree.GetEntry(n_event)
            for key in all_scan_points.keys():
                if getattr(tree, "GenModel_" + key):
                    all_scan_points[key].Enter(n_event)

        print("Scan points found:")
        for scan_point in sorted(all_scan_points):
            print("\t%s: %d events" % (scan_point, all_scan_points[scan_point].GetN()))

        # Now we reactivate all branches so we save the whole tree!
        tree.SetBranchStatus("*", 1)
        for drop in options.drop:
            tree.SetBranchStatus(drop, 0)
        for keep in options.keep:
            tree.SetBranchStatus(keep, 1)

        # The actual saving
        print("Saving the split files")
        for scan_point, event_list in tqdm(
            all_scan_points.iteritems(), total=len(all_scan_points)
        ):
            output = os.path.join(
                options.output,
                os.path.basename(fname).replace(".root", "_%s.root" % scan_point),
            )
            if os.path.exists(output):
                raise RuntimeError("Output file already exists")

            with RootFileManager(output, "recreate") as f_out:
                tree.SetEventList(event_list)
                out = tree.CopyTree("1")
                f_out.WriteTObject(out, "Events")
                f_out.Write()

    return all_scan_points.keys()


def split_files_parallel(args):
    all_scan_points = []

    if args.jobs == 1:
        all_scan_points = [point for f in input_files for point in splitfile([f, args])]
    else:
        with closing(Pool(args.jobs)) as pool:
            chunk_size = max(1, len(input_files) // (args.jobs * 4))
            inputs = [(f, args) for f in input_files]
            result = pool.map_async(splitfile, inputs, chunk_size)
            result.wait()

            for sublist in result.get():
                all_scan_points.extend(sublist)

    return list(set(all_scan_points))


def hadd_files(outdir, name):
    cmd = [
        "python",
        "haddnano.py",
        os.path.join(outdir, "%s_merged.root" % name),
        os.path.join(outdir, "*%s*root" % name),
    ]
    print("Merging: %s" % name)
    process = subprocess.Popen(
        " ".join(cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    return


def merge_files_parallel(args):
    if not args.hadd:
        return
    if args.jobs == 1:
        for p in all_scan_points:
            hadd_files(args.output, p)
        return

    with closing(Pool(args.jobs)) as pool:
        inputs = [(args.output, point) for point in all_scan_points]
        result = pool.map_async(hadd_files, inputs)
        result.wait()


if __name__ == "__main__":
    args = get_args()

    # Get the list of input files
    input_files = get_input_files(args.input)

    # Splitting section
    print("Splitting the following files: %s\n" % input_files)
    all_scan_points = split_files_parallel(args)

    # Merging section
    print("All scan points: %s\n" % all_scan_points)
    merge_files_parallel(args)
