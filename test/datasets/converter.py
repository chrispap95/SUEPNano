# This script can be used to convert dataset names between different years.
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
        help="Input JSON file. Make sure the desired primary datasets are inside.",
        default="2016/full_mc_2016.json",
    )
    parser.add_argument(
        "--secondary",
        type=str,
        help="Secondary dataset name. Example: RunIISummer20UL16MiniAODv2-106X_mcRun2_asymptotic_v17",
        default="RunIISummer20UL16MiniAODv2-106X_mcRun2_asymptotic_v17",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    with open(args.input) as json_file:
        datasets = json.load(json_file)

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

    with open(args.input.replace(".json", "_correct.json"), "w") as json_file:
        json.dump(list_of_datasets, json_file, indent=4)
