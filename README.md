# SUEPNano

This is a [NanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD) framework for the analysis of SUEPs - plain NanoAOD, extended by PF candidates and more track information. 
This format can be used with [fastjet](http://fastjet.fr) directly.

## Recipe

**THIS IS A DEVELOPMENT BRANCH**

For UL data and MC **NanoAODv9** according to the [XPOG](https://gitlab.cern.ch/cms-nanoAOD/nanoaod-doc/-/wikis/Releases/NanoAODv9) and [PPD](https://twiki.cern.ch/twiki/bin/viewauth/CMS/PdmVAnalysisSummaryTable) recommendations:

```
cmsrel  CMSSW_10_6_26
cd  CMSSW_10_6_26/src
cmsenv
git cms-addpkg PhysicsTools/NanoAOD
git clone -b ul https://github.com/SUEPPhysics/SUEPNano.git PhysicsTools/SUEPNano
scram b -j 2
cd PhysicsTools/SUEPNano/test
```

Note: if the `git cms-addpkg PhysicsTools/NanoAOD` doesn't work, make sure that you have forked the [CMSSW](https://github.com/cms-sw/cmssw) to your user, and configured your git correctly: `git config --global user.github <your github username>`.

Note: This configuration has been tested for this combination of CMSSW release, global tag, era and dataset. When running over a new dataset you should check with [the nanoAOD workbook twiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD#Running_on_various_datasets_from) to see if the era modifiers in the CRAB configuration files are correct. The jet correction versions are taken from the global tag.

## Local Usage:

2018 MC:
```
cmsRun ul18_mc_NANO.py
```


