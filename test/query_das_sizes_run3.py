#!/usr/bin/env python
from __future__ import print_function, division
import subprocess
import json
import time
from collections import defaultdict
import sys
import re


def format_size(size_in_bytes):
    """Convert bytes to human readable format"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_in_bytes < 1024.0:
            return "{:.2f} {}".format(size_in_bytes, unit)
        size_in_bytes /= 1024.0


def query_das(dataset):
    """Query DAS for dataset size"""
    try:
        cmd = 'dasgoclient --query="dataset={} summary" --json'.format(dataset)
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        if stderr:
            print("Warning for {}: {}".format(dataset, stderr))
        if not stdout:
            return 0
        data = json.loads(stdout)
        if not data:
            return 0
        # Get size in bytes from the summary
        return sum(item.get("summary", [{}])[0].get("file_size", 0) for item in data)
    except Exception as e:
        print("Error querying {}: {}".format(dataset, e))
        return 0


def categorize_dataset(dataset_name):
    """Categorize dataset based on its name"""
    categories = {
        "DYJetsToLL_M-50_TuneCP5_13p6TeV-madgraphMLM-pythia8": "DYJetsToLL_M-50_TuneCP5_13p6TeV-madgraphMLM-pythia8",
        "DYTo2L_MLL-50_TuneCP5_13p6TeV_pythia8": "DYTo2L_MLL-50_TuneCP5_13p6TeV_pythia8",
        "DYto2L-2Jets_MLL-50_NJ_TuneCP5_13p6TeV_amcatnloFXFX-pythia8": r"DYto2L-2Jets_MLL-50_[0-2]J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8",
        "DYto2L-2Jets_MLL-50_PTLL_NJ_TuneCP5_13p6TeV_amcatnloFXFX-pythia8": r"DYto2L-2Jets_MLL-50_PTLL-(?:40to100|100to200|200to400|400to600|600)_[0-2]J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8",
        "DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8": "DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8",
        "DYto2L-4Jets_MLL-50_NJ_TuneCP5_13p6TeV_madgraphMLM-pythia8": r"DYto2L-4Jets_MLL-50_[0-4]J_TuneCP5_13p6TeV_madgraphMLM-pythia8",
        "DYto2L-4Jets_MLL-50_PTLL_TuneCP5_13p6TeV_madgraphMLM-pythia8": r"DYto2L-4Jets_MLL-50_PTLL-(?:40to100|100to200|200to400|400to600|600)_TuneCP5_13p6TeV_madgraphMLM-pythia8",
        "DYto2L-4Jets_MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8": "DYto2L-4Jets_MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8",
    }

    for category, pattern in categories.items():
        if re.search(pattern, dataset_name):
            return category
    return "Other"


def load_datasets(txt_file):
    """Load dataset names from JSON file"""
    try:
        with open(txt_file, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print("Error loading JSON file: {}".format(e))
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: {} <datasets.txt>".format(sys.argv[0]))
        sys.exit(1)

    # Load datasets from JSON file
    datasets = load_datasets(sys.argv[1])
    print("Loaded {} datasets from txt file".format(len(datasets)))

    # Initialize storage for results
    group_sizes = defaultdict(int)
    dataset_sizes = {}
    categorized_datasets = defaultdict(list)
    total_size = 0  # Track grand total
    total_datasets = 0  # Track total number of datasets with size > 0

    print("\nQuerying DAS for dataset sizes...")
    print("-" * 50)

    # Query each dataset and categorize it
    for dataset in datasets:
        print("Querying {}...".format(dataset))
        size = query_das(dataset)
        if size > 0:
            total_datasets += 1
            total_size += size
        dataset_sizes[dataset] = size
        category = categorize_dataset(dataset)
        categorized_datasets[category].append(dataset)
        group_sizes[category] += size
        time.sleep(1)  # Add delay to avoid overwhelming the service

    # Print results
    print("\nResults Summary:")
    print("=" * 50)
    print("Total number of datasets queried: {}".format(len(datasets)))
    print("Datasets found in DAS: {}".format(total_datasets))
    print("Total size of all datasets: {}\n".format(format_size(total_size)))

    print("Breakdown by category:")
    print("-" * 50)

    # Sort categories by total size
    sorted_categories = sorted(group_sizes.items(), key=lambda x: x[1], reverse=True)

    # Calculate percentage for each category
    for category, size in sorted_categories:
        if size > 0:  # Only show categories with data
            percentage = (size / float(total_size)) * 100
            print("\n{}:".format(category))
            print(
                "Total size: {} ({:.1f}% of total)".format(
                    format_size(size), percentage
                )
            )
            print("Individual datasets:")
            # Sort datasets within category by size
            sorted_datasets = sorted(
                [(d, dataset_sizes[d]) for d in categorized_datasets[category]],
                key=lambda x: x[1],
                reverse=True,
            )
            for dataset, dataset_size in sorted_datasets:
                if dataset_size > 0:
                    dataset_percentage = (dataset_size / float(total_size)) * 100
                    print(
                        "  {}: {} ({:.1f}% of total)".format(
                            dataset, format_size(dataset_size), dataset_percentage
                        )
                    )

    print("\n" + "=" * 50)
    print("Grand total: {}".format(format_size(total_size)))
    print("Total datasets: {}".format(total_datasets))


if __name__ == "__main__":
    main()
