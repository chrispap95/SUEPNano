import json
import time
import argparse
from multiprocessing import Process
from CRABClient import UserUtilities
from CRABAPI import RawCommand

running_options = ["isCRAB=True"]

def make_request_name(sample):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return sample + "_" + timestamp

def make_config(args, sample, dataset):
    config_ = UserUtilities.config()

    config_.General.workArea = 'crab_' + args.campaign
    config_.General.transferOutputs = True
    config_.General.transferLogs = True

    config_.JobType.pluginName = 'Analysis'
    config_.JobType.psetName = 'NANO_cfg.py' 
    config_.JobType.maxMemoryMB = 2000
    config_.JobType.pyCfgParams = running_options
    config_.JobType.allowUndistributedCMSSW = True

    config_.Data.inputDBS = 'global'
    config_.Data.splitting = 'FileBased'
    config_.Data.publication = False
    config_.Data.unitsPerJob = 1
    config_.Data.totalUnits = 1
    config_.Data.outLFNDirBase = args.output
    config_.Site.storageSite = 'T3_US_FNALLPC'

    config_.General.requestName = make_request_name(sample)
    config_.Data.inputDataset = dataset
    config_.Data.outputDatasetTag = sample
    
    return config_

def submit(config):
    res = RawCommand.crabCommand('submit', config = config)
    return

def get_args():
    parser = argparse.ArgumentParser(description='Submit CRAB jobs')
    parser.add_argument(
        '-d', '--dataset', type=str, help='JSON file with dataset names', required=True
    )
    parser.add_argument(
        '-c', '--campaign', type=str, help='Name of the campaign for the CRAB area', default='NANO_UL18'
    )
    parser.add_argument(
        '-o', 
        '--output', 
        type=str, 
        help='Output location', 
        default='/store/group/lpcsuep/Muon_counting_search/SUEPNano_Nov2024'
    )
    parser.add_argument(
        '--dryrun', action='store_true', help='Dry run - print the commands without executing them'
    )
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = get_args()

    datasets = {}
    with open(args.dataset, 'r') as f:
        datasets = json.load(f)

    for sample in datasets:
        config = make_config(args, sample, datasets[sample])
        if args.dryrun:
            print(config.pythonise_())
            print
            continue
        p = Process(target=submit, args=(config,))
        p.start()
        p.join()
