import argparse
import glob
import os
import subprocess
from tqdm import tqdm  # type: ignore [import]
import ROOT  # type: ignore [import]


def get_args():
    parser = argparse.ArgumentParser(
        description="Split a root file into multiple files based on scan points."
    )
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
    return parser.parse_args()


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


def get_gen_models_from_runs(file_in):
    runs_tree = file_in.Get("Runs")
    return [
        branch.GetName().replace("genEventCount_", "")
        for branch in runs_tree.GetListOfBranches()
        if "genEventCount_" in branch.GetName()
    ]


def get_event_list_per_model(f_in):
    # Create a dictionary with the event list for each model
    event_list_per_model = {}

    # Get the number of events in the input file
    tree = f_in.Get("Events")
    n_events = tree.GetEntriesFast()

    # If there are no events, return an empty dictionary
    if n_events == 0:
        return event_list_per_model

    # Check if the tree has any GenModel branches
    branches = [key.GetName() for key in tree.GetListOfBranches()]
    genmodel_branches = [
        branch.replace("GenModel_", "") for branch in branches if "GenModel" in branch
    ]

    # If there are no GenModel branches, return an empty dictionary
    if len(genmodel_branches) == 0:
        return event_list_per_model

    # Initialize the entry list for each model
    for model in genmodel_branches:
        event_list_per_model[model] = ROOT.TEntryList(model, model)

    # Turn off all branches except GenModel to speed up the process
    tree.SetBranchStatus("*", 0)
    tree.SetBranchStatus("GenModel*", 1)

    # Loop over all events and fill the entry list for each model
    for n_event in tqdm(xrange(n_events), desc="Scanning events", unit="Events"):  # type: ignore [name-defined]
        tree.GetEntry(n_event)
        for model in genmodel_branches:
            if getattr(tree, "GenModel_" + model):
                event_list_per_model[model].Enter(n_event)

    tree.SetBranchStatus("*", 1)
    return event_list_per_model


def copy_runs_tree(tree_in, model):
    """
    This seems to work although ROOT people say it is not possible.
    """
    tree_in.SetBranchStatus("*SUEP*", 0)
    tree_in.SetBranchStatus("*" + model, 1)
    tree_out = tree_in.CopyTree("1")
    for branch in tree_out.GetListOfBranches():
        if branch.GetName().endswith(model):
            branch.SetName(branch.GetName().replace("_" + model, ""))
            branch.SetTitle(
                branch.GetTitle()
                .replace(", for model label " + model, "")
                .replace("_" + model, "")
            )
            for leaf in branch.GetListOfLeaves():
                leaf.SetName(leaf.GetName().replace("_" + model, ""))
                leaf.SetTitle(leaf.GetTitle().replace("_" + model, ""))
    return tree_out


def splitting(args, input_file):
    """
    Split one input file into multiple output files based on the gen models found.
    """
    # Load input file and get list of keys
    f_in = ROOT.TFile.Open(input_file, "read")
    keys = list(set([key.GetName() for key in f_in.GetListOfKeys()]))

    # Get list of gen models using the Runs tree
    gen_models = get_gen_models_from_runs(f_in)

    # Get which events correspond to which gen model
    event_list_per_model = get_event_list_per_model(f_in)

    # For each gen model, create a new file with the corresponding entries
    for model in tqdm(gen_models, desc="Saving models", unit="files"):
        output_file_name = os.path.join(
            args.output,
            os.path.basename(input_file).replace(".root", "_%s.root" % model),
        )
        f_out = ROOT.TFile.Open(output_file_name, "recreate")
        for key in keys:
            if key == "Events":
                tree_in = f_in.Get(key)

                if tree_in.GetEntriesFast() > 0:
                    # Drop all GenModel branches
                    tree_in.SetBranchStatus("GenModel*", 0)

                    # Keep only the events corresponding to the model
                    if model in event_list_per_model:
                        tree_in.SetEntryList(event_list_per_model[model])
                    else:
                        tree_in.SetEntryList(ROOT.TEntryList())

                tree_out = tree_in.CopyTree("1")
                f_out.WriteTObject(tree_out, key, "Overwrite")
            elif key == "Runs":
                tree_in = f_in.Get(key)
                tree_out = copy_runs_tree(tree_in, model)
                f_out.WriteTObject(tree_out, key, "Overwrite")
            elif key == "LuminosityBlocks":
                tree_in = f_in.Get(key)
                tree_out = tree_in.CloneTree(-1, "fast")
                f_out.WriteTObject(tree_out, key, "Overwrite")

        f_out.Close()

    f_in.Close()

    return gen_models


def split_wrapper(args, input_files):
    all_scan_points = set()
    for i, input_file in enumerate(input_files, 1):
        print("Splitting file {}/{}: {}".format(i, len(input_files), input_file))
        all_scan_points.update(splitting(args, input_file))
    return all_scan_points


def hadd_files(args, scan_point):
    cmd = [
        "python",
        "haddnano.py",
        os.path.join(args.output, "%s_merged.root" % scan_point),
        os.path.join(args.output, "*%s.root" % scan_point),
    ]
    print("Merging: %s" % scan_point)
    process = subprocess.Popen(
        " ".join(cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    return


def merge_wrapper(args, all_scan_points):
    if not args.hadd:
        return
    for scan_point in all_scan_points:
        hadd_files(args, scan_point)


if __name__ == "__main__":
    args = get_args()

    # Get input files
    input_files = get_input_files(args.input)

    # Make sure the output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # Split the input files
    all_scan_points = split_wrapper(args, input_files)

    # Merge the output files
    merge_wrapper(args, all_scan_points)
