"""
This script can be used to convert dataset names between different years.
It takes a JSON file as input, which contains the desired primary datasets,
and a secondary dataset name which is the target MC campaign. It then queries
the DAS (Data Aggregation Service) to get the list of datasets for the
specified primary and secondary datasets. The output is a JSON file
containing the list of datasets.

Usage:
    python converter.py --input <input_json_file> --secondary <secondary_dataset_name>
Example (to get 2022EE from 2022):
    python converter.py --input 2022/full_mc_2022.json --secondary Run3Summer22EEMiniAODv4-130X_mcRun3_2022_realistic_postEE_v6

Secondary dataset names:
    - Run3Summer22EEMiniAODv4-130X_mcRun3_2022_realistic_postEE_v
    - Run3Summer22MiniAODv4-130X_mcRun3_2022_realistic_v
    - Run3Summer23BPixMiniAODv4-130X_mcRun3_2023_realistic_postBPix_v
    - Run3Summer23MiniAODv4-130X_mcRun3_2023_realistic_v
"""

import argparse
import json
import shlex
import subprocess
from tqdm import tqdm  # type: ignore[import]


def get_args():
    parser = argparse.ArgumentParser(
        description="Convert dataset names between different years."
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input JSON file. Make sure the desired primary datasets are inside. E.g., 2022/full_mc_2022.json",
        required=True,
    )
    parser.add_argument(
        "--secondary",
        type=str,
        help="Secondary dataset name. Example: Run3Summer22EEMiniAODv4-130X_mcRun3_2022_realistic_postEE_v6",
        required=True,
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file. Default is <input_json_file>_correct.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    with open(args.input) as json_file:
        datasets = json.load(json_file)

    # Get the primary dataset names from the input JSON file
    # and remove duplicates
    primaries = list(set([p.split("/")[1] for p in datasets]))

    list_of_datasets = []
    for primary in tqdm(primaries):
        command = "dasgoclient -query='dataset=/{}/{}*/MINIAODSIM'".format(
            primary, args.secondary
        )
        p = subprocess.Popen(
            shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = p.communicate()
        list_of_datasets += [f for f in out.decode("utf-8").split("\n") if f]

    output_file = args.output
    if output_file is None:
        output_file = args.input.replace(".json", "_correct.json")
    with open(output_file, "w") as json_file:
        json.dump(sorted(list_of_datasets), json_file, indent=4)
