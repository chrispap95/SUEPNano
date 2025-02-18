import ROOT  # type: ignore [import]
import numpy
import sys


def zero_fill(tree, br_name, br_obj, allow_non_bool=False):
    # typename: (numpy type code, root type code)
    branch_type_dict = {
        "Bool_t": ("?", "O"),
        "Float_t": ("f4", "F"),
        "UInt_t": ("u4", "i"),
        "Long64_t": ("i8", "L"),
        "Double_t": ("f8", "D"),
    }
    brType = br_obj.GetLeaf(br_name).GetTypeName()
    if (not allow_non_bool) and (brType != "Bool_t"):
        print(
            (
                "Did not expect to back fill non-boolean branches",
                tree,
                br_name,
                br_obj.GetLeaf(br).GetTypeName(),
            )
        )
    else:
        if brType not in branch_type_dict:
            raise RuntimeError("Impossible to backfill branch of type %s" % brType)
        buff = numpy.zeros(1, dtype=numpy.dtype(branch_type_dict[brType][0]))
        b = tree.Branch(br_name, buff, br_name + "/" + branch_type_dict[brType][1])
        # be sure we do not trigger flushing
        b.SetBasketSize(tree.GetEntries() * 2)
        for x in range(0, tree.GetEntries()):
            b.Fill()
        b.ResetAddress()


def open_files(input_files):
    file_handles = []
    go_fast = True

    for input_file in input_files:
        print("Adding file" + str(input_file))
        file_handle = ROOT.TFile.Open(input_file)
        if not file_handle or file_handle.IsZombie():
            print("Error opening file %s" % input_file)
            continue
        file_handles.append(file_handle)
        if len(file_handles) > 1 and (
            file_handle.GetCompressionSettings()
            != file_handles[0].GetCompressionSettings()
        ):
            go_fast = False
            print("Disabling fast merging as inputs have different compressions")
    return file_handles, go_fast


def abbreviate_list(lst, max_items=5):
    """Returns a string with an abbreviated list if it's too long."""
    if len(lst) > max_items:
        return (
            str(lst[:max_items])[:-1]
            + ", ... ("
            + str(len(lst) - max_items)
            + " more)]"
        )
    return str(lst)


if "__main__" in __name__:
    # Input & output
    if len(sys.argv) < 3:
        print("Syntax: haddnano.py out.root input1.root input2.root ...")
        sys.exit(1)

    output_filename = sys.argv[1]
    input_files = sys.argv[2:]

    # Open all input files
    file_handles, go_fast = open_files(input_files)

    if not file_handles:
        print("No valid input files found")
        sys.exit(1)

    # Create output file
    output_file = ROOT.TFile(output_filename, "recreate")
    if go_fast:
        output_file.SetCompressionSettings(file_handles[0].GetCompressionSettings())
    output_file.cd()

    # Loop over all keys in first file: this loops over all top-level objects (TTrees)
    for key in file_handles[0].GetListOfKeys():
        name = key.GetName()
        print("Merging tree: " + str(name))
        obj = key.ReadObj()
        cl = ROOT.TClass.GetClass(key.GetClassName())
        inputs = ROOT.TList()

        # Make sure we are merging trees
        is_tree = obj.IsA().InheritsFrom(ROOT.TTree.Class())
        if not is_tree:
            print(
                "Cannot handle "
                + str(obj.IsA().GetName())
                + ". Not a TTree. Skipping..."
            )
            continue

        obj = obj.CloneTree(-1, "fast" if go_fast else "")
        branch_names = set([x.GetName() for x in obj.GetListOfBranches()])

        # Loop over all input files. Will merge the specified trees from all input files
        for i_fh, fh in enumerate(file_handles[1:], start=1):
            other_obj = fh.GetListOfKeys().FindObject(name).ReadObj()
            if other_obj.GetEntries() == 0:
                print("No entries, moving on.")
                continue
            inputs.Add(other_obj)
            print("Merging tree " + name + " from file " + str(i_fh + 1))
            if obj.GetName() == "Events":
                other_obj.SetAutoFlush(0)
                other_branches = set(
                    [x.GetName() for x in other_obj.GetListOfBranches()]
                )
                missing_branches = list(branch_names - other_branches)
                additional_branches = list(other_branches - branch_names)
                print(
                    "\tMissing: "
                    + abbreviate_list(missing_branches)
                    + "\n\tAdditional: "
                    + abbreviate_list(additional_branches)
                )
                for br in missing_branches:
                    # fill "Other"
                    print("checkpoint 1")
                    zero_fill(other_obj, br, obj.GetListOfBranches().FindObject(br))
                for br in additional_branches:
                    # fill main
                    print("checkpoint 2")
                    branch_names.add(br)
                    zero_fill(obj, br, other_obj.GetListOfBranches().FindObject(br))
            if obj.GetName() == "Runs":
                other_obj.SetAutoFlush(0)
                other_branches = set(
                    [x.GetName() for x in other_obj.GetListOfBranches()]
                )
                missing_branches = list(branch_names - other_branches)
                additional_branches = list(other_branches - branch_names)
                print(
                    "\tMissing: "
                    + abbreviate_list(missing_branches)
                    + "\n\tAdditional: "
                    + abbreviate_list(additional_branches)
                )
                for br in missing_branches:
                    # fill "Other"
                    zero_fill(
                        other_obj,
                        br,
                        obj.GetListOfBranches().FindObject(br),
                        allow_non_bool=True,
                    )
                for br in additional_branches:
                    # fill main
                    branch_names.add(br)
                    zero_fill(
                        obj,
                        br,
                        other_obj.GetListOfBranches().FindObject(br),
                        allow_non_bool=True,
                    )
            # merge immediately
            obj.Merge(inputs, "fast" if go_fast else "")
            inputs.Clear()

        obj.Write()

    output_file.Close()
