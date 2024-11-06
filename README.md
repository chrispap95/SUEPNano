# SUEPNano

This is a [NanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD) framework for the analysis of SUEPs - plain NanoAOD, extended by PF candidates and more track information. 
This format can be used with [fastjet](http://fastjet.fr) directly.

## Recipe

**THIS IS A FORK FOR THE MUON COUNTING ANALYSIS**

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

The samples processed with the scripts in this reposiotry are skimmed to include only the events that pass the desired HLT path and have at least three muons that pass basic quality criteria.


## Local Usage:
```
cmsRun NANO_cfg.py isMC=True era=2018 maxEvents=10 verbose=True inputFiles=file:/path/to/your/file.root
```
The input file should be AOD or miniAOD.

## For Centrally produced SUEP samples with multiple points in the scan:

splitTrees.py can be used to split a set of input nanoAOD samples based on the correponding gen-level setup and -optionally- merge the resulting chunks together (i.e. same signal point coming from different nanosuep files). Usage is:

```
python splitTrees.py --input [input directory] --output [output directory] --jobs [number of cores] --hadd 
```

haddnano.py is just a modified version of the standard cms-sw tool to reduce verbosity a bit


