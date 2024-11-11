# SUEPNano
**THIS IS A FORK FOR THE MUON COUNTING ANALYSIS**

This is a [NanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD) framework for the analysis of SUEPs. This fork is specialized for the Muon counting search for SUEPs. This is plain NanoAOD, extended by PF candidates and more track information, plus skimming for the HLT path and the preselection. This format can be used with [fastjet](http://fastjet.fr) directly.

## Recipe

For UL data and MC **NanoAODv9** according to the [XPOG](https://gitlab.cern.ch/cms-nanoAOD/nanoaod-doc/-/wikis/Releases/NanoAODv9) and [PPD](https://twiki.cern.ch/twiki/bin/viewauth/CMS/PdmVAnalysisSummaryTable) recommendations:

```
cmsrel  CMSSW_10_6_44 # or the newest 10_6_X release
cd  CMSSW_10_6_44/src
cmsenv
git cms-addpkg PhysicsTools/NanoAOD
git clone -b ul https://github.com/chrispap95/SUEPNano.git PhysicsTools/SUEPNano
scram b -j 8
cd PhysicsTools/SUEPNano/test
```

*Note:* if the `git cms-addpkg PhysicsTools/NanoAOD` doesn't work, make sure that you have forked the [CMSSW](https://github.com/cms-sw/cmssw) to your user, and configured your git correctly: `git config --global user.github <your github username>`.

*Note:* This configuration has been tested for this combination of CMSSW release, global tag, era and dataset. When running over a new dataset you should check with [the nanoAOD workbook twiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD#Running_on_various_datasets_from) to see if the era modifiers in the CRAB configuration files are correct. The jet correction versions are taken from the global tag.


## Skimming
The samples processed with the scripts in this reposiotry are skimmed to include only the events that pass the desired HLT path:
```
    "HLT_TripleMu_10_5_5_DZ_v*" OR
    "HLT_TripleMu_12_10_5_v*" OR
    "HLT_TripleMu_5_3_3_Mass3p8_DZ_v*" OR
    "HLT_TripleMu_5_3_3_Mass3p8to60_DZ_v*"
```
and have at least three muons that pass the basic quality requirements. The `genEventSumw` before the skimming is included in the Runs tree as `genEventSumwPreSkim` for normalization purposes.


## Local Usage:
```
cmsRun NANO_cfg.py isMC=True era=2018 maxEvents=10 verbose=True inputFiles=file:/path/to/your/file.root
```
The input file should be AOD or miniAOD.

## CRAB Usage:
The following command will submit jobs to the CRAB to process the datasets in the `datasets.json` file and store the output in the `/store/group/lpcsuep/Muon_counting_search/SUEPNano_Nov2024` directory:
```
python multicrab.py -d datasets.json -c NANO_UL18 -o /store/group/lpcsuep/Muon_counting_search/SUEPNano_Nov2024
```
You can look at the crab configs before submitting them by using the `--nosubnit` option. If you want to submit only one job for validation purposes, you can use the `--validation` option.

The status can be checked with the usual crab commands or with the `crab_monitor.py` script:
```
python crab_monitor.py -d filenames/QCD.json
```
This will create a summary table for the latest submissions for the datasets in the `QCD.json` file and it will save the status details in a file in the directory `crab_monitor_history`. If you want to focus on the submissions that are not finished, you can process this file with the `process_crab_status.py` script:
```
python process_crab_status.py -i crab_monitor_history/filename.csv
```
and create an `incomplete_datasets.json` file to use for further monitoring and resubmissions.

To resubmit the failed jobs, you can try to resubmit all submissions by using `crab_resubmit_all.sh` or you can resubmit only selected datasets by using the `crab_resubmit.py` script:
```
python crab_resubmit.py -d incomplete_datasets.json --maxmemory 4000 --maxjobruntime 500
```
This will resubmit the failed jobs for the datasets in the `incomplete_datasets.json` file with the specified memory and runtime limits.


## For Centrally produced SUEP samples with multiple points in the scan:

splitTrees.py can be used to split a set of input nanoAOD samples based on the correponding gen-level setup and -optionally- merge the resulting chunks together (i.e. same signal point coming from different nanosuep files). Usage is:

```
python splitTrees.py --input [input directory] --output [output directory] --jobs [number of cores] --hadd 
```

haddnano.py is just a modified version of the standard cms-sw tool to reduce verbosity a bit


