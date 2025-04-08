"""
Script to submit CRAB jobs for multiple datasets

Example usage:
python multicrab.py -d datasets.json -c NANO_UL18 -o /store/group/lpcsuep/Muon_counting_search/SUEPNano_Nov2024/
"""

import argparse
import json
import time
from tqdm import tqdm  # type: ignore[import]
from multiprocessing import Process
from CRABClient import UserUtilities
from CRABAPI import RawCommand

running_options = ["isCRAB=True"]


def get_args():
    parser = argparse.ArgumentParser(description="Submit CRAB jobs")
    parser.add_argument(
        "-d", "--dataset", type=str, help="JSON file with dataset names", required=True
    )
    parser.add_argument(
        "-c",
        "--campaign",
        type=str,
        help="Name of the campaign for the CRAB area",
    )
    parser.add_argument(
        "-e",
        "--era",
        type=str,
        help="Era of the dataset (e.g. 2016APV, 2016, 2017, 2018)",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output location",
    )
    parser.add_argument(
        "--nosubmit",
        action="store_true",
        help="Do not submit the jobs, just print the commands",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Dry run - will try to benchmark the jobs. Note: Does not work well for now. Do not use.",
    )
    parser.add_argument(
        "--validation",
        action="store_true",
        help="Submit a validation job with 1 unit",
    )
    parser.add_argument(
        "--mc",
        action="store_true",
        help="To be set if the dataset is MC",
    )
    parser.add_argument(
        "--data",
        action="store_true",
        help="To be set if the dataset is data",
    )
    parser.add_argument(
        "--process-partial",
        action="store_true",
        help="Process only the part of the dataset that is on disk",
    )
    parser.add_argument(
        "--units-per-job",
        type=int,
        help="Number of units per job. Default is 10.",
        default=10,
    )
    args = parser.parse_args()
    return args


def make_dataset_tag(dataset, long=False):
    if long:
        return dataset.replace("/", "_")[1:]
    return dataset.split("/")[1]


def make_request_name(dataset, long=False):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return make_dataset_tag(dataset, long=long) + "_" + timestamp


def make_config(args, dataset):
    config_ = UserUtilities.config()

    config_.General.workArea = "crab_" + args.campaign
    config_.General.transferOutputs = True
    config_.General.transferLogs = True
    config_.General.requestName = make_request_name(dataset, long=args.data)

    config_.JobType.pluginName = "Analysis"
    config_.JobType.psetName = "NANO_data_cfg.py" if args.data else "NANO_mc_cfg.py"
    config_.JobType.maxMemoryMB = 3000
    config_.JobType.pyCfgParams = running_options + ["era=" + args.era]
    config_.JobType.allowUndistributedCMSSW = True
    config_.JobType.maxJobRuntimeMin = 1200

    config_.Data.inputDBS = "global"
    config_.Data.splitting = "FileBased"
    config_.Data.publication = False
    config_.Data.unitsPerJob = args.units_per_job
    if args.validation:
        config_.Data.unitsPerJob = 1
        config_.Data.totalUnits = 1
    config_.Data.outLFNDirBase = args.output
    config_.Data.inputDataset = dataset
    config_.Data.outputDatasetTag = make_dataset_tag(dataset, long=args.data)
    if args.process_partial:
        config_.Data.partialDataset = True

    config_.Site.storageSite = "T3_US_FNALLPC"

    return config_


def submit(config, args):
    res = RawCommand.crabCommand("submit", config=config, dryrun=args.dryrun)
    return


if __name__ == "__main__":
    args = get_args()

    if args.campaign is None:
        raise ValueError("Please provide a campaign name. Example: NANO_UL18")
    if args.output is None:
        raise ValueError(
            "Please provide an output location. Example: /store/group/lpcsuep/Muon_counting_search/SUEPNano_UL18_Nov2024"
        )
    if not (args.data or args.mc):
        raise ValueError("Please specify either --data or --mc")

    datasets = []
    with open(args.dataset, "r") as f:
        datasets = json.load(f)

    for dataset in tqdm(datasets, desc="Submitting CRAB jobs"):
        config = make_config(args, dataset)
        if args.nosubmit:
            print(config.pythonise_())
            print
            continue
        p = Process(target=submit, args=(config, args))
        p.start()
        p.join()
