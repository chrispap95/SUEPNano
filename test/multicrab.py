"""
Script to submit CRAB jobs for multiple datasets

Example usage:
python multicrab.py -d datasets.json -c NANO_UL18 -o /store/group/lpcsuep/Muon_counting_search/SUEPNano_Nov2024/
"""

import json
import time
import argparse
from multiprocessing import Process
from CRABClient import UserUtilities
from CRABAPI import RawCommand

running_options = ["isCRAB=True"]


def make_dataset_tag(dataset):
    return dataset.split("/")[1]


def make_request_name(dataset):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return make_dataset_tag(dataset) + "_" + timestamp


def make_config(args, dataset):
    config_ = UserUtilities.config()

    config_.General.workArea = "crab_" + args.campaign
    config_.General.transferOutputs = True
    config_.General.transferLogs = True
    config_.General.requestName = make_request_name(dataset)

    config_.JobType.pluginName = "Analysis"
    config_.JobType.psetName = "NANO_data_cfg.py" if args.isdata else "NANO_mc_cfg.py"
    config_.JobType.maxMemoryMB = 3000
    config_.JobType.pyCfgParams = running_options
    config_.JobType.allowUndistributedCMSSW = True
    config_.JobType.maxJobRuntimeMin = 400

    config_.Data.inputDBS = "global"
    config_.Data.splitting = "FileBased"
    config_.Data.publication = False
    config_.Data.unitsPerJob = 10
    if args.validation:
        config_.Data.unitsPerJob = 1
        config_.Data.totalUnits = 1
    config_.Data.outLFNDirBase = args.output
    config_.Data.inputDataset = dataset
    config_.Data.outputDatasetTag = make_dataset_tag(dataset)

    config_.Site.storageSite = "T3_US_FNALLPC"

    return config_


def submit(config, args):
    res = RawCommand.crabCommand("submit", config=config, dryrun=args.dryrun)
    return


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
        default="NANO_UL18",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output location",
        default="/store/group/lpcsuep/Muon_counting_search/SUEPNano_Nov2024",
    )
    parser.add_argument(
        "--nosubmit",
        action="store_true",
        help="Do not submit the jobs, just print the commands",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Dry run - will try to benchmark the jobs",
    )
    parser.add_argument(
        "--validation",
        action="store_true",
        help="Submit a validation job with 1 unit",
    )
    parser.add_argument(
        "--isdata",
        action="store_true",
        help="To be set if the dataset is data",
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = get_args()

    datasets = []
    with open(args.dataset, "r") as f:
        datasets = json.load(f)

    for dataset in datasets:
        config = make_config(args, dataset)
        if args.nosubmit:
            print(config.pythonise_())
            print
            continue
        p = Process(target=submit, args=(config, args))
        p.start()
        p.join()
