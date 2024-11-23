# Run using: cmsRun NANO_cfg.py outputFile=YYY.root maxEvents=ZZZ
# It will do the following in order:
#   1) run over the input miniAOD file(s)
#   2) apply a skim to select events of interest using the HLT path and the muon selections
#   2) produce a nanoAOD file with the skimmed events including the PF candidates.

import FWCore.ParameterSet.Config as cms

# Set parameters externally
from FWCore.ParameterSet.VarParsing import VarParsing

params = VarParsing("analysis")

params.register(
    "isMC",
    True,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.bool,
    "Flag to indicate whether the sample is simulation or data",
)

params.setDefault("maxEvents", -1)

params.setDefault("inputFiles", "miniaod.root")

params.setDefault("outputFile", "nano_skim.root")

params.register(
    "era", "2018", VarParsing.multiplicity.singleton, VarParsing.varType.string, "era"
)

params.register(
    "cpu",
    8,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.int,
    "number of threads to use",
)

params.register(
    "verbose",
    False,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.bool,
    "Flag to indicate whether the verbose output is enabled",
)

params.register(
    "isCRAB",
    False,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.bool,
    "Flag to indicate whether the job is run in CRAB",
)


# Parse command line arguments
params.parseArguments()
if params.verbose:
    print(params)

# Define the process
if params.era == "2016apv":
    from Configuration.Eras.Era_Run2_2016_HIPM_cff import Run2_2016_HIPM as era
elif params.era == "2016":
    from Configuration.Eras.Era_Run2_2016_cff import Run2_2016 as era
elif params.era == "2017":
    from Configuration.Eras.Era_Run2_2017_cff import Run2_2017 as era
elif params.era == "2018":
    from Configuration.Eras.Era_Run2_2018_cff import Run2_2018 as era
else:
    raise ValueError("Invalid era: %s" % params.era)

from Configuration.Eras.Modifier_run2_nanoAOD_106Xv2_cff import run2_nanoAOD_106Xv2

process = cms.Process("NANO", era, run2_nanoAOD_106Xv2)

# import of standard configurations
process.load("Configuration.StandardSequences.Services_cff")
process.load("SimGeneral.HepPDTESSource.pythiapdt_cfi")
process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.EventContent.EventContent_cff")
if params.isMC:
    process.load("SimGeneral.MixingModule.mixNoPU_cfi")
process.load("Configuration.StandardSequences.GeometryRecoDB_cff")
if params.isMC:
    process.load("Configuration.StandardSequences.MagneticField_cff")
else:
    process.load("Configuration.StandardSequences.MagneticField_AutoFromDBCurrent_cff")
process.load("HLTrigger.HLTfilters.hltHighLevel_cfi")
process.load("PhysicsTools.NanoAOD.nano_cff")
process.load("Configuration.StandardSequences.EndOfProcess_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")

process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(params.maxEvents))

# outputFile = params.outputFile
# override input parameter
outputFile = "nano_skim.root"

# Input source
process.source = cms.Source(
    "PoolSource",
    fileNames=cms.untracked.vstring("file:file.root"),
    secondaryFileNames=cms.untracked.vstring(),
    skipBadFiles=cms.untracked.bool(True),
)

process.options = cms.untracked.PSet(
    # SkipEvent=cms.untracked.vstring("ProductNotFound")
)

# Production Info
process.configurationMetadata = cms.untracked.PSet(
    annotation=cms.untracked.string("--python_filename nevts:-1"),
    name=cms.untracked.string("Applications"),
    version=cms.untracked.string("$Revision: 1.19 $"),
)

# Output definition
if params.isMC:
    process.NANOAODSIMoutput = cms.OutputModule(
        "NanoAODOutputModule",
        compressionAlgorithm=cms.untracked.string("LZMA"),
        compressionLevel=cms.untracked.int32(9),
        dataset=cms.untracked.PSet(
            dataTier=cms.untracked.string("NANOAODSIM"),
            filterName=cms.untracked.string(""),
        ),
        fileName=cms.untracked.string(outputFile),
        outputCommands=(process.NANOAODSIMEventContent.outputCommands),
        fakeNameForCrab=cms.untracked.bool(params.isCRAB),
        SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring("skim_step")),
    )
else:
    process.NANOAODoutput = cms.OutputModule(
        "NanoAODOutputModule",
        compressionAlgorithm=cms.untracked.string("LZMA"),
        compressionLevel=cms.untracked.int32(9),
        dataset=cms.untracked.PSet(
            dataTier=cms.untracked.string("NANOAOD"),
            filterName=cms.untracked.string(""),
        ),
        fileName=cms.untracked.string(outputFile),
        outputCommands=(process.NANOAODEventContent.outputCommands),
        fakeNameForCrab=cms.untracked.bool(params.isCRAB),
        SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring("skim_step")),
    )

# Additional output definition
# Other statements
from Configuration.AlCa.GlobalTag import GlobalTag

if params.isMC:
    if params.era == "2016apv":
        process.GlobalTag = GlobalTag(
            process.GlobalTag, "106X_mcRun2_asymptotic_preVFP_v11", ""
        )
    elif params.era == "2016":
        process.GlobalTag = GlobalTag(
            process.GlobalTag, "106X_mcRun2_asymptotic_v17", ""
        )
    elif params.era == "2017":
        process.GlobalTag = GlobalTag(process.GlobalTag, "106X_mc2017_realistic_v9", "")
    elif params.era == "2018":
        process.GlobalTag = GlobalTag(
            process.GlobalTag, "106X_upgrade2018_realistic_v16_L1v1", ""
        )
else:
    process.GlobalTag = GlobalTag(process.GlobalTag, "106X_dataRun2_v35", "")

# Keep track of the gen weights
if params.isMC:
    process.genWeightSum = cms.EDProducer(
        "GenWeightsTablePreSkimProducer",
        genEvent=cms.InputTag("generator"),
    )
    process.genweight_step = cms.Path(process.genWeightSum)
    process.NANOAODSIMoutput.outputCommands.extend(
        [
            "keep nanoaodMergeableCounterTable_genWeightSum_*_*",
        ]
    )

# HLT filter and skimmer
if params.era == "2016apv" or params.era == "2016":
    process.load("PhysicsTools.SUEPNano.hlt_skim_2016_cff")
elif params.era == "2017":
    process.load("PhysicsTools.SUEPNano.hlt_skim_2017_cff")
elif params.era == "2018":
    process.load("PhysicsTools.SUEPNano.hlt_skim_2018_cff")
else:
    raise ValueError("Invalid era: %s" % params.era)
process.load("PhysicsTools.SUEPNano.muon_skim_cff")
process.skim_step = cms.Path(process.hltHighLevel * process.muon_skim)

# And also at the start of the nano not to run code that we don't need
process.nanoSequenceMC.insert(0, process.muon_skim)
process.nanoSequenceMC.insert(0, process.hltHighLevel)
if params.isMC:
    process.nanoSequenceMC.insert(0, process.genWeightSum)

# Path and EndPath definitions
process.nanoAOD_step = (
    cms.Path(process.nanoSequenceMC) if params.isMC else cms.Path(process.nanoSequence)
)
process.endjob_step = cms.EndPath(process.endOfProcess)

# Schedule definition
if params.isMC:
    process.NANOAODSIMoutput_step = cms.EndPath(process.NANOAODSIMoutput)
    process.schedule = cms.Schedule(
        process.genweight_step,
        process.skim_step,
        process.nanoAOD_step,
        process.endjob_step,
        process.NANOAODSIMoutput_step,
    )
else:
    process.NANOAODoutput_step = cms.EndPath(process.NANOAODoutput)
    process.schedule = cms.Schedule(
        process.skim_step,
        process.nanoAOD_step,
        process.endjob_step,
        process.NANOAODoutput_step,
    )
from PhysicsTools.PatAlgos.tools.helpers import associatePatAlgosToolsTask

associatePatAlgosToolsTask(process)

# Setup FWK for multithreaded
process.options.numberOfThreads = cms.untracked.uint32(params.cpu)
process.options.numberOfStreams = cms.untracked.uint32(0)

# customisation of the process.

# Automatic addition of the customisation function from PhysicsTools.NanoAOD.nano_cff
if params.isMC:
    from PhysicsTools.NanoAOD.nano_cff import nanoAOD_customizeMC

    process = nanoAOD_customizeMC(process)
else:
    from PhysicsTools.NanoAOD.nano_cff import nanoAOD_customizeData

    process = nanoAOD_customizeData(process)

# Automatic addition of the customisation function from PhysicsTools.SUEPNano.nano_suep_cff
from PhysicsTools.SUEPNano.nano_suep_cff import SUEPNano_customize

# call to customisation function SUEPNano_customize imported from PhysicsTools.SUEPNano.nano_suep_cff
process = SUEPNano_customize(process)

process.nanoSequenceMC.remove(process.rivetProducerHTXS)
process.nanoSequenceMC.remove(process.HTXSCategoryTable)

# End of customisation functions

if not params.isMC:
    # Automatic addition of the customisation function from Configuration.DataProcessing.Utils
    from Configuration.DataProcessing.Utils import addMonitoring

    # call to customisation function addMonitoring imported from Configuration.DataProcessing.Utils
    process = addMonitoring(process)

# Customisation from command line
process.add_(cms.Service("InitRootHandlers", EnableIMT=cms.untracked.bool(False)))

if not params.verbose:
    process.MessageLogger.cerr.FwkReport.reportEvery = 1000

# Add early deletion of temporary data products to reduce peak memory need
from Configuration.StandardSequences.earlyDeleteSettings_cff import customiseEarlyDelete

process = customiseEarlyDelete(process)
# End adding early deletion
