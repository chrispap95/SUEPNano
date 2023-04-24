import FWCore.ParameterSet.Config as cms
import FWCore.Utilities.FileUtils as FileUtils
import os

# Set parameters externally 
from FWCore.ParameterSet.VarParsing import VarParsing
params = VarParsing('analysis')

params.register(
    'isMC', 
    False, 
    VarParsing.multiplicity.singleton,VarParsing.varType.bool,
    'Flag to indicate whether the sample is simulation or data'
)

params.setDefault(
    'maxEvents', 
    -1
)

params.setDefault(
    'outputFile', 
    'YYY.root' 
)

params.register(
  "era",
  "2018",
  VarParsing.multiplicity.singleton,VarParsing.varType.string,
  "era"
)

# Define the process
process = cms.Process("LL")

# Parse command line arguments
params.parseArguments()

# How many events to process
process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(params.maxEvents) )


if params.isMC == True:
    if params.era == "2016":
        os.system('cmsRun ' +os.environ['CMSSW_BASE']+'/src/PhysicsTools/SUEPNano/test/NANO_MC_2016.py')
    elif params.era == "2016apv":
        os.system('cmsRun ' +os.environ['CMSSW_BASE']+'/src/PhysicsTools/SUEPNano/test/NANO_MC_2016apv.py')
    elif params.era == "2017":
        os.system('cmsRun ' +os.environ['CMSSW_BASE']+'/src/PhysicsTools/SUEPNano/test/NANO_MC_2017.py')
    elif params.era == "2018":
        os.system('cmsRun ' +os.environ['CMSSW_BASE']+'/src/PhysicsTools/SUEPNano/test/NANO_MC_2018.py')
    else:
        print("Era is nonsensical")
else:
    if params.era == "2016":
        os.system('cmsRun ' +os.environ['CMSSW_BASE']+'/src/PhysicsTools/SUEPNano/test/NANO_data_2016.py')
    elif params.era == "2016_HIPM":
        os.system('cmsRun ' +os.environ['CMSSW_BASE']+'/src/PhysicsTools/SUEPNano/test/NANO_data_2016_HIPM.py')
    elif params.era == "2017":
        os.system('cmsRun ' +os.environ['CMSSW_BASE']+'/src/PhysicsTools/SUEPNano/test/NANO_data_2017.py')
    elif params.era == "2018":
        os.system('cmsRun ' +os.environ['CMSSW_BASE']+'/src/PhysicsTools/SUEPNano/test/NANO_data_2018.py')
    else:
        print("Era is nonsensical")
