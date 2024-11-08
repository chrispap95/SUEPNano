"""
Run this script to merge files from different directories on EOS.
Produce a JSON file with the merged files.
To be implemented: submit the merging jobs to condor.
"""

import subprocess
import argparse
import json
import os

# Redirector for FNAL LPC EOS
eos_redirector = "root://cmseos.fnal.gov/"
# 1GB max size. This is the target size for the output files
max_size = 1 * 1024 * 1024 * 1024


def eos_ls(directory):
    """List files in a directory on EOS"""
    command = "source ~/.bash_profile 2>/dev/null; eos {} ls {}".format(
        eos_redirector, directory
    )
    result = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, executable="/bin/bash"
    )
    out, err = result.communicate()
    return out.decode("utf-8").strip().split("\n")


def eos_file_size(file_path):
    """Get the size of a file on EOS in bytes"""
    command = "source ~/.bash_profile 2>/dev/null; eos {} stat {}".format(
        eos_redirector, file_path
    )
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


def merge_files(file_list, output_file):
    """Merge files in file_list using haddnano.py and save to output_file"""
    command = (
        ["python", "haddnano.py"]
        + ["temp.root"]
        + ["root://cmseos.fnal.gov/" + f_i for f_i in file_list]
    )
    subprocess.check_call(command)
    command = ["xrdcp", "temp.root", "root://cmseos.fnal.gov/" + output_file]
    subprocess.check_call(command)
    os.remove("temp.root")


def process_directory(args, directory):
    subdir = directory.split("/")[
        -4
    ]  # Adjusting to get the correct subdir name for JSON
    json_data = {}
    files = eos_ls(directory)

    if not files:
        return json_data

    file_list = [
        os.path.join(directory, file) for file in files if file.endswith(".root")
    ]
    merged_files = []
    temp_files = []
    temp_size = 0
    file_index = 1

    for file in file_list:
        size = eos_file_size(file)
        if temp_size + size > max_size:
            output_file = os.path.join(
                output_base_dir, "{}/skim_{}.root".format(subdir, file_index)
            )
            merge_files(temp_files, output_file)
            merged_files.append(output_file)
            temp_files = []
            temp_size = 0
            file_index += 1

        temp_files.append(file)
        temp_size += size

    if temp_files:
        output_file = os.path.join(
            output_base_dir, "{}/skim_{}.root".format(subdir, file_index)
        )
        merge_files(temp_files, output_file)
        merged_files.append(output_file)

    json_data[subdir] = [
        "root://cmseos.fnal.gov//{}".format(output_file) for output_file in merged_files
    ]

    return json_data


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Merge files from different directories"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input base directory",
        default="/store/user/chpapage/SUEPNano_Jul2024",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output base directory",
        default="/store/user/chpapage/SUEPNano_Jul2024_merged",
    )
    parser.add_argument(
        "--max_size", type=int, default=max_size, help="Maximum size of output files"
    )
    return parser.parse_args()


if __name__ == "__main__":
    all_data = {}
    for directory in directories:
        data = process_directory(directory)
        all_data.update(data)

    json_output = "merged_files.json"
    with open(json_output, "w") as json_file:
        json.dump(all_data, json_file, indent=4)

    print("JSON file created: {}".format(json_output))
