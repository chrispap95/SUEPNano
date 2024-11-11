#!/usr/bin/env python2
from __future__ import print_function
import json
import argparse
import glob
import os
import sys
import subprocess


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Resubmit incomplete CRAB tasks")
    parser.add_argument(
        "-d",
        "--datasets",
        required=True,
        help="Input JSON file with list of incomplete datasets",
    )
    parser.add_argument(
        "--crab-dir",
        default="crab_NANO_UL18",
        help="Base directory containing CRAB task directories (default: crab_NANO_UL18)",
    )
    parser.add_argument(
        "--maxmemory",
        type=int,
        default=4000,
        help="Maximum memory in MB (e.g., 4000 for 4GB)",
    )
    parser.add_argument(
        "--maxjobruntime",
        type=int,
        default=480,
        help="Maximum runtime in minutes (e.g., 480 for 6 hours)",
    )
    return parser.parse_args()


def get_primary_name(dataset):
    """Extract primary dataset name from full dataset path"""
    return dataset.split("/")[1]


def find_latest_task_dir(crab_base_dir, primary_name):
    """Find the most recent task directory for a given primary dataset name"""
    pattern = os.path.join(crab_base_dir, "crab_" + primary_name + "*")
    matching_dirs = glob.glob(pattern)

    if not matching_dirs:
        return None

    # Sort by modification time (most recent last)
    latest_dir = max(matching_dirs, key=os.path.getmtime)
    return latest_dir


def main():
    args = get_args()

    try:
        # Read the JSON file
        with open(args.datasets, "r") as f:
            datasets = json.load(f)

        print("Found {} datasets to resubmit".format(len(datasets)))

        # Build command options
        cmd_options = ""
        if args.maxmemory:
            print("Setting maxMemoryMB to {} MB".format(args.maxmemory))
            cmd_options += " --maxmemory={}".format(args.maxmemory)
        if args.maxjobruntime:
            print("Setting maxJobRuntimeMin to {} minutes".format(args.maxjobruntime))
            cmd_options += " --maxjobruntime={}".format(args.maxjobruntime)

        for i, dataset in enumerate(datasets, 1):
            print("\nProcessing dataset {}/{}:".format(i, len(datasets)))
            print("  Dataset: {}".format(dataset))

            # Find corresponding task directory
            primary_name = get_primary_name(dataset)
            task_dir = find_latest_task_dir(args.crab_dir, primary_name)

            if not task_dir:
                print("  ERROR: Could not find task directory for {}".format(dataset))
                continue

            print("  Task directory: {}".format(task_dir))

            # Build and execute crab resubmit command
            cmd = "crab resubmit " + cmd_options + " " + task_dir
            print("  Executing: {}".format(cmd))

            try:
                subprocess.check_call(cmd, shell=True)
                print("  Successfully resubmitted")
            except subprocess.CalledProcessError as e:
                print("  ERROR: Failed to resubmit: {}".format(str(e)))

    except Exception as e:
        print("Error: {}".format(str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
