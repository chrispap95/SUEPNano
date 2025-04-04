# SUEPNano

NOTE: **THIS IS A FORK FOR THE MUON COUNTING ANALYSIS – Branch for Run3**

This is a [NanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD) framework for the analysis of SUEPs. This fork is specialized for the Muon counting search for SUEPs. This is plain NanoAOD, extended by PF candidates and more track information, plus skimming for the HLT path and the preselection. This format can be used with [fastjet](http://fastjet.fr) directly.

## Recipe

For Run3 data and MC **NanoAODv12** according to the [XPOG](https://gitlab.cern.ch/cms-nanoAOD/nanoaod-doc/-/wikis/Releases/NanoAODv12) and [PPD](https://twiki.cern.ch/twiki/bin/viewauth/CMS/PdmVRun3Analysis) recommendations:

```bash
cmssw-el8 # needed for newer el9 interactive nodes
cmsrel CMSSW_13_0_13 # this is the recommended version for NanoAODv12
cd CMSSW_13_0_13/src
cmsenv
git cms-addpkg PhysicsTools/NanoAOD
git clone -b Run3 https://github.com/chrispap95/SUEPNano.git PhysicsTools/SUEPNano
scram b -j 8
cd PhysicsTools/SUEPNano/test
```

*Note:* if the `git cms-addpkg PhysicsTools/NanoAOD` doesn't work, make sure that you have forked the [CMSSW](https://github.com/cms-sw/cmssw) to your user, and configured your git correctly: `git config --global user.github <your github username>`.

*Note:* This configuration has been tested for this combination of CMSSW release, global tag, era and dataset. When running over a new dataset you should check with [the nanoAOD workbook twiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD#Running_on_various_datasets_from) to see if the era modifiers in the CRAB configuration files are correct. The jet correction versions are taken from the global tag.

*Note:* sometimes (on lxplus especially) you might have to execute `source /cvmfs/cms.cern.ch/common/crab-setup.sh` before running the `crab` commands.

## Skimming

The samples processed with the scripts in this reposiotry are skimmed to include only the events that pass the desired HLT path:

```python
    "HLT_TripleMu_10_5_5_DZ_v*" OR
    "HLT_TripleMu_12_10_5_v*" OR
    "HLT_TripleMu_5_3_3_Mass3p8_DZ_v*"
```

and have at least three muons that pass the basic quality requirements. The `genEventSumw` before the skimming is included in the Runs tree as `genEventSumwPreSkim` for normalization purposes.

## Local Usage

```bash
cmsRun NANO_cfg.py isMC=True era=2022 maxEvents=10 verbose=True inputFiles=file:/path/to/your/file.root
```

The input file should be AOD or miniAOD.

## CRAB Usage

The following command will submit jobs to the CRAB to process the datasets in the `datasets.json` file and store the output in the `/store/group/lpcsuep/Muon_counting_search/SUEPNano_2022_Apr2025` directory:

```bash
python multicrab.py -d datasets.json -c NANO_2022 -o /store/group/lpcsuep/Muon_counting_search/SUEPNano_2022_Apr2025
```

You can look at the crab configs before submitting them by using the `--nosubnit` option. If you want to submit only one job for validation purposes, you can use the `--validation` option. These can be useful if you are submitting for the first time.

The status can be checked with the CRAB grafana website, the usual crab commands or with the `crab_monitor.py` script:

```bash
python crab_monitor.py -d filenames/2022/full_mc_2022.json --crab-dir crab_NANO_2022
```

This will create a summary table for the latest submissions for the datasets in the `QCD.json` file and it will save the status details in a file in the directory `crab_monitor_history`. If you want to focus on the submissions that are not finished, you can process this file with the `process_crab_status.py` script:

```bash
python process_crab_status.py -i crab_monitor_history/filename.csv
```

and create an `filename_incomplete.json` file to use for further monitoring and resubmissions.

To resubmit the failed jobs, you can try to resubmit all submissions by using `crab_resubmit_all.sh` or you can resubmit only selected datasets by using the `crab_resubmit.py` script:

```bash
python crab_resubmit.py -d incomplete_datasets.json --crab-dir crab_NANO_2022 --maxmemory 4000 --maxjobruntime 500
```

This will resubmit the failed jobs for the datasets in the `filename_incomplete.json` file with the specified memory and runtime limits.

## For Centrally produced SUEP samples with multiple points in the scan

`split_trees.py` can be used to split a set of input nanoAOD samples based on the correponding gen-level setup and -optionally- merge the resulting chunks together (i.e. same signal point coming from different nanosuep files). Usage is:

```bash
python split_trees.py --input [input directory] --output [output directory] --hadd 
```

To submit condor jobs for splitting, you can use the `splitter.py` script:

```bash
python splitter.py -d datasets/2022/GluGluToSUEP_2022.json --json --input /store/group/lpcsuep/Muon_counting_search/SUEPNano_2022_Apr2025 --output /store/group/lpcsuep/Muon_counting_search/SUEPNano_2022_Apr2025
./condor_split_<timestamp>/submit_all.sh
```

## Merging the output

The output root files can be merged with the `haddnano.py` script:

```bash
python haddnano.py merged.root input_files/*.root
```

You can submit condor jobs for merging with the `merge.py` script:

```bash
python merge.py --dataset datasets/2022/GluGluToSUEP_2022.json --input /store/group/lpcsuep/Muon_counting_search/SUEPNano_2022_Apr2025
./condor_merge_<timestamp>/submit_all.sh
```

You should check the options of the script with `python merge.py --help` before running it.

**Note:** you can skip the `--dataset` option if you want to scan all files in the input directory. This is useful for processing the data datasets:

```bash
python merge.py --input /store/group/lpcsuep/Muon_counting_search/SUEPNano_2022_Apr2025/DoubleMuon --output /store/group/lpcsuep/Muon_counting_search/SUEPNano_2022_Apr2025_merged/
```

Similarly, to process the split signal samples, you can do something like this:

```bash
for era in 2022 2022EE 2023 2023BPix; do
    for suep in $(eosls /store/user/lpcsuep/Muon_counting_search/SUEPNano_${era}_Apr2025/ | grep "SUEP.*split"); do
        basepath=/store/user/lpcsuep/Muon_counting_search
        python merge.py --input ${basepath}/SUEPNano_${era}_Apr2025/$suep --output ${basepath}/SUEPNano_${era}_Apr2025/$suep
        ./$(ls -td -- condor_merge* | head -n 1)/submit_all.sh
    done
done
```
