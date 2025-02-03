# This script can be used to convert dataset names between different years.
import json
import shlex
import subprocess
from tqdm import tqdm  # type: ignore[import]

if __name__ == "__main__":
    with open("2016APV/full_mc_2016APV.json") as json_file:
        datasets = json.load(json_file)

    list_of_datasets = []
    for dataset in tqdm(datasets):
        primary = dataset.split("/")[1]
        secondary = "RunIISummer20UL16MiniAODAPVv2-106X_mcRun2_asymptotic_preVFP_v11"
        command = "dasgoclient -query='dataset=/{}/{}*/MINIAODSIM'".format(
            primary, secondary
        )
        p = subprocess.Popen(
            shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = p.communicate()
        list_of_datasets.append([f for f in out.decode("utf-8").split("\n") if f])

    with open("2016APV/full_mc_2016APV_correct.json", "w") as json_file:
        json.dump(list_of_datasets, json_file, indent=4)
