#!/bin/env python
import ROOT  # type: ignore [import]
import numpy
import sys


def zero_fill(tree, branch_name, branch_object, allow_non_bool=False):
    # typename: (numpy type code, root type code)
    branch_type_dict = {
        "Bool_t": ("?", "O"),
        "Float_t": ("f4", "F"),
        "UInt_t": ("u4", "i"),
        "Long64_t": ("i8", "L"),
        "Double_t": ("f8", "D"),
    }
    branch_type = branch_object.GetLeaf(branch_name).GetTypeName()
    if (not allow_non_bool) and (branch_type != "Bool_t"):
        print(
            (
                "Did not expect to back fill non-boolean branches",
                tree,
                branch_name,
                branch_object.GetLeaf(branch_name).GetTypeName(),
            )
        )
    else:
        if branch_type not in branch_type_dict:
            raise RuntimeError("Impossible to backfill branch of type %s" % branch_type)
        buffer = numpy.zeros(1, dtype=numpy.dtype(branch_type_dict[branch_type][0]))
        branch = tree.Branch(
            branch_name, buffer, branch_name + "/" + branch_type_dict[branch_type][1]
        )
        # be sure we do not trigger flushing
        branch.SetBasketSize(tree.GetEntries() * 2)
        for x in range(0, tree.GetEntries()):
            branch.Fill()
        branch.ResetAddress()


def get_tree_branches(tree):
    """Get branch names from a TTree, handling empty trees."""
    if tree and tree.GetEntries() > 0:
        return set([branch.GetName() for branch in tree.GetListOfBranches()])
    return set()


def find_first_nonempty_tree(file_handles, tree_name):
    """Find the first file that has a non-empty tree with the given name."""
    for file_handle in file_handles:
        key = file_handle.GetListOfKeys().FindObject(tree_name)
        if not key:
            continue
        tree = key.ReadObj()
        if tree.GetEntries() > 0:
            return tree
    return None


def handle_tree_merge(main_tree, other_tree, tree_name, go_fast):
    """Handle merging of two TTrees, properly handling empty trees."""
    inputs = ROOT.TList()

    # Skip empty trees
    if other_tree.GetEntries() == 0:
        print("Skipping empty tree %s from input file" % tree_name)
        return main_tree

    # If main tree is empty, clone the structure from other_tree
    if main_tree.GetEntries() == 0:
        print("Main tree %s is empty, cloning structure from input file" % tree_name)
        main_tree = other_tree.CloneTree(0)

    other_tree.SetAutoFlush(0)

    # Get branch names from both trees
    main_branches = get_tree_branches(main_tree)
    other_branches = get_tree_branches(other_tree)

    # Handle missing and additional branches
    missing_branches = list(main_branches - other_branches)
    additional_branches = list(other_branches - main_branches)

    if missing_branches or additional_branches:
        print("For tree %s:" % tree_name)
        print("missing: " + str(missing_branches))
        print("Additional: " + str(additional_branches))

    # Fill missing branches in other tree
    for branch in missing_branches:
        zero_fill(
            other_tree,
            branch,
            main_tree.GetListOfBranches().FindObject(branch),
            allow_non_bool=(tree_name == "Runs"),
        )

    # Fill additional branches in main tree
    for branch in additional_branches:
        main_branches.add(branch)
        zero_fill(
            main_tree,
            branch,
            other_tree.GetListOfBranches().FindObject(branch),
            allow_non_bool=(tree_name == "Runs"),
        )

    # Merge trees
    inputs.Add(other_tree)
    main_tree.Merge(inputs, "fast" if go_fast else "")
    inputs.Clear()

    return main_tree


if "__main__" in __name__:
    # Input & output
    if len(sys.argv) < 3:
        print("Syntax: haddnano.py out.root input1.root input2.root ...")
        sys.exit(1)

    output_filename = sys.argv[1]
    input_files = sys.argv[2:]

    # Open the input files and the output file
    file_handles = []
    go_fast = True
    for file_in in input_files:
        print("Adding file " + str(file_in))
        file_handle = ROOT.TFile.Open(file_in)
        if not file_handle or file_handle.IsZombie():
            print("Error opening file %s" % file_in)
            continue
        file_handles.append(file_handle)
        if len(file_handles) > 1 and (
            file_handle.GetCompressionSettings()
            != file_handles[0].GetCompressionSettings()
        ):
            go_fast = False
            print("Disabling fast merging as inputs have different compressions")

    if not file_handles:
        print("No valid input files found")
        sys.exit(1)

    output_file = ROOT.TFile(output_filename, "recreate")
    if go_fast:
        output_file.SetCompressionSettings(file_handles[0].GetCompressionSettings())
    output_file.cd()

    # Collect all unique keys across all files
    all_keys = set()
    for file_handle in file_handles:
        for key in file_handle.GetListOfKeys():
            all_keys.add(key.GetName())

    # Process each unique key
    for name in all_keys:
        print("Merging " + str(name))

        # Find first non-empty tree if it's a known tree type
        first_obj = None
        if name in ["Events", "Runs"]:
            first_obj = find_first_nonempty_tree(file_handles, name)
            if first_obj is None:
                print("Warning: No non-empty %s tree found in any input file" % name)
                continue

        # If not a special tree type or no non-empty tree found, use first file's object
        if first_obj is None:
            first_key = file_handles[0].GetListOfKeys().FindObject(name)
            if not first_key:
                print("Warning: %s not found in first file" % name)
                continue
            first_obj = first_key.ReadObj()

        inputs = ROOT.TList()
        is_tree = first_obj.IsA().InheritsFrom(ROOT.TTree.Class())

        if is_tree:
            obj = first_obj.CloneTree(-1, "fast" if go_fast else "")

            # Handle each input file
            for file_handle in file_handles:
                if file_handle == file_handles[0] and first_obj == file_handle.Get(
                    name
                ):
                    continue  # Skip if this is the file we used as our reference

                other_key = file_handle.GetListOfKeys().FindObject(name)
                if not other_key:
                    print("Warning: %s not found in %s" % (name, file_handle.GetName()))
                    continue

                other_obj = other_key.ReadObj()
                if name in ["Events", "Runs"]:
                    obj = handle_tree_merge(obj, other_obj, name, go_fast)
                else:
                    inputs.Add(other_obj)
                    obj.Merge(inputs, "fast" if go_fast else "")
                    inputs.Clear()

            obj.Write()

        elif first_obj.IsA().InheritsFrom(ROOT.TH1.Class()):
            obj = first_obj
            for file_handle in file_handles:
                if file_handle == file_handles[0] and first_obj == file_handle.Get(
                    name
                ):
                    continue
                other_key = file_handle.GetListOfKeys().FindObject(name)
                if other_key:
                    inputs.Add(other_key.ReadObj())
            obj.Merge(inputs)
            obj.Write()

        elif first_obj.IsA().InheritsFrom(ROOT.TObjString.Class()):
            obj = first_obj
            for file_handle in file_handles:
                if file_handle == file_handles[0] and first_obj == file_handle.Get(
                    name
                ):
                    continue
                other_key = file_handle.GetListOfKeys().FindObject(name)
                if other_key:
                    st = other_key.ReadObj()
                    if st.GetString() != obj.GetString():
                        print("Strings are not matching")
            obj.Write()

        else:
            print("Cannot handle " + str(first_obj.IsA().GetName()))

    output_file.Close()
    for file_handle in file_handles:
        file_handle.Close()
