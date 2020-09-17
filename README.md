# SUEPNano

This is a [NanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD) framework for the analysis of SUEPs - plain NanoAOD, extended by PF candidates and more track information. 
This format can be used with [fastjet](http://fastjet.fr) directly.

## Recipe

**THIS IS A DEVELOPMENT BRANCH**

For **UL** 2016, 2017 and 2018 data and MC **NanoAODv6** according to the [XPOG](https://gitlab.cern.ch/cms-nanoAOD/nanoaod-doc/-/wikis/Releases/NanoAODv6) and [PPD](https://twiki.cern.ch/twiki/bin/view/CMS/PdmVLegacy2017Analysis) recommendations:

```
cmsrel  CMSSW_10_6_14
cd  CMSSW_10_6_14/src
cmsenv
git cms-addpkg PhysicsTools/NanoAOD
git clone https://github.com/dr-stringfellow/SUEPNano.git PhysicsTools/SUEPNano
scram b -j 10
cd PhysicsTools/SUEPNano/test
```
Note: This configuration has been tested for this combination of CMSSW release, global tag, era and dataset. When running over a new dataset you should check with [the nanoAOD workbook twiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD#Running_on_various_datasets_from) to see if the era modifiers in the CRAB configuration files are correct. The jet correction versions are taken from the global tag.

## Local Usage:

2017 MC:
```
cmsRun nano106X_on_mini106X_2017_mc_NANO.py
```

## How to create website with nanoAOD content

To create nice websites like [this one](http://algomez.web.cern.ch/algomez/testWeb/JMECustomNano102x_mc_v01.html#Jet) with the content of nanoAOD, use the `inspectNanoFile.py` file from the `PhysicsTools/nanoAOD` package as:
```
python PhysicsTools/NanoAOD/test/inspectNanoFile.py NANOAOD.root -s website_with_collectionsize.html -d website_with_collectiondescription.html
```

