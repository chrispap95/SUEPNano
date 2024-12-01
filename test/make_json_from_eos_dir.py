from __future__ import print_function
import argparse
import json
import subprocess
import os
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dir", help="EOS directory path", required=True)
parser.add_argument(
    "-o",
    "--output",
    help="Output JSON file name",
    default="dataset_files.json",
    required=False,
)

xrootd_redirector = "root://cmseos.fnal.gov/"


def get_files_recursive(path):
    files = []
    result = subprocess.check_output(
        "eos {} ls {}".format(xrootd_redirector, path), shell=True
    )
    items = result.decode("utf-8").splitlines()

    for item in items:
        full_path = os.path.join(path, item)
        if item.endswith(".root"):
            files.append(os.path.join(xrootd_redirector + full_path))

    return files


if __name__ == "__main__":
    args = parser.parse_args()

    # Get all datasets in the top directory
    print("Listing datasets in {}".format(args.dir))
    result = subprocess.check_output(
        "eos {} ls {}".format(xrootd_redirector, args.dir), shell=True
    )
    datasets = result.decode("utf-8").splitlines()

    print("Found {} datasets".format(len(datasets)))

    file_dict = {}

    for dataset in tqdm(datasets):
        if dataset:  # ignore empty lines
            dataset_path = os.path.join(args.dir, dataset)
            file_dict[dataset] = get_files_recursive(dataset_path)

    # Write the dictionary to a JSON file
    with open(args.output, "w") as f:
        json.dump(file_dict, f, indent=4, sort_keys=True)
