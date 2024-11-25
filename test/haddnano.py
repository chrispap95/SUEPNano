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


if "__main__" in __name__:
    # Input & output
    if len(sys.argv) < 3:
        print("Syntax: haddnano.py out.root input1.root input2.root ...")
    output_filename = sys.argv[1]
    input_files = sys.argv[2:]

    # Open the input files and the output file and enable fast merging if the compression settings are the same
    file_handles = []
    go_fast = True
    for file_in in input_files:
        print("Adding file" + str(file_in))
        file_handles.append(ROOT.TFile.Open(file_in))
        if (
            file_handles[-1].GetCompressionSettings()
            != file_handles[0].GetCompressionSettings()
        ):
            go_fast = False
            print("Disabling fast merging as inputs have different compressions")
    output_file = ROOT.TFile(output_filename, "recreate")
    if go_fast:
        output_file.SetCompressionSettings(file_handles[0].GetCompressionSettings())
    output_file.cd()

    # Get the list of keys (e.g., TTrees) in the first file and loop over them to merge
    for key in file_handles[0].GetListOfKeys():
        name = key.GetName()
        print("Merging" + str(name))
        object = key.ReadObj()
        inputs = ROOT.TList()
        is_tree = object.IsA().InheritsFrom(ROOT.TTree.Class())
        if is_tree:
            object = object.CloneTree(-1, "fast" if go_fast else "")
            branch_names = set(
                [branch.GetName() for branch in object.GetListOfBranches()]
            )
        # Loop over all the other input files, find the object with the same name and merge
        # If the object is a TTree and some branches are missing or are additional, fill them with zeros where needed
        for file_handle in file_handles[1:]:
            other_object = file_handle.GetListOfKeys().FindObject(name).ReadObj()
            inputs.Add(other_object)
            # Skip this file if the tree is empty
            if is_tree and object.GetEntries() == 0:
                continue
            if is_tree and object.GetName() == "Events":
                other_object.SetAutoFlush(0)
                other_branches = set(
                    [branch.GetName() for branch in other_object.GetListOfBranches()]
                )
                missing_branches = list(branch_names - other_branches)
                additional_branches = list(other_branches - branch_names)
                print(
                    "missing: "
                    + str(missing_branches)
                    + "\n Additional:"
                    + str(additional_branches)
                )
                for branch in missing_branches:
                    # fill "Other"
                    zero_fill(
                        other_object,
                        branch,
                        object.GetListOfBranches().FindObject(branch),
                    )
                for branch in additional_branches:
                    # fill main
                    branch_names.add(branch)
                    zero_fill(
                        object,
                        branch,
                        other_object.GetListOfBranches().FindObject(branch),
                    )
            if is_tree and object.GetName() == "Runs":
                other_object.SetAutoFlush(0)
                other_branches = set(
                    [branch.GetName() for branch in other_object.GetListOfBranches()]
                )
                missing_branches = list(branch_names - other_branches)
                additional_branches = list(other_branches - branch_names)
                print(
                    "missing: "
                    + str(missing_branches)
                    + "\n Additional:"
                    + str(additional_branches)
                )
                for branch in missing_branches:
                    # fill "Other"
                    zero_fill(
                        other_object,
                        branch,
                        object.GetListOfBranches().FindObject(branch),
                        allow_non_bool=True,
                    )
                for branch in additional_branches:
                    # fill main
                    branch_names.add(branch)
                    zero_fill(
                        object,
                        branch,
                        other_object.GetListOfBranches().FindObject(branch),
                        allow_non_bool=True,
                    )
                # merge immediately for trees
            if is_tree:
                object.Merge(inputs, "fast" if go_fast else "")
                inputs.Clear()

        if is_tree:
            object.Write()
        elif object.IsA().InheritsFrom(ROOT.TH1.Class()):
            object.Merge(inputs)
            object.Write()
        elif object.IsA().InheritsFrom(ROOT.TObjString.Class()):
            for st in inputs:
                if st.GetString() != object.GetString():
                    print("Strings are not matching")
            object.Write()
        else:
            print("Cannot handle " + str(object.IsA().GetName()))
