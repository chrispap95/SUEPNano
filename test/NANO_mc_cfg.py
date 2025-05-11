# Run using: cmsRun NANO_mc_cfg.py outputFile=YYY.root maxEvents=ZZZ
# It will do the following in order:
#   1) run over the input miniAOD file(s)
#   2) apply a skim to select events of interest using the HLT path and the muon selections
#   2) produce a nanoAOD file with the skimmed events including the PF candidates.

import FWCore.ParameterSet.Config as cms

# Set parameters externally
from FWCore.ParameterSet.VarParsing import VarParsing

params = VarParsing("analysis")

params.setDefault("maxEvents", -1)

params.setDefault("inputFiles", "miniaod.root")

params.setDefault("outputFile", "nano_skim.root")

params.register(
    "era", "2022", VarParsing.multiplicity.singleton, VarParsing.varType.string, "era"
)

params.register(
    "cpu",
    1,
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
print(params)

# Define the process
if "2022" in params.era:
    from Configuration.Eras.Era_Run3_cff import Run3 as era
elif "2023" in params.era:
    from Configuration.Eras.Era_Run3_2023_cff import Run3_2023 as era
else:
    raise ValueError("Invalid era: %s" % params.era)

process = cms.Process('NANO', era)

# import of standard configurations
process.load("Configuration.StandardSequences.Services_cff")
process.load("SimGeneral.HepPDTESSource.pythiapdt_cfi")
process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.EventContent.EventContent_cff")
process.load("SimGeneral.MixingModule.mixNoPU_cfi")
process.load("Configuration.StandardSequences.GeometryRecoDB_cff")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("HLTrigger.HLTfilters.hltHighLevel_cfi")
process.load("PhysicsTools.NanoAOD.nano_cff")
process.load("Configuration.StandardSequences.EndOfProcess_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")

process.maxEvents = cms.untracked.PSet(
    input=cms.untracked.int32(params.maxEvents),
    output = cms.optional.untracked.allowed(cms.int32,cms.PSet)
)

# Input source
if params.inputFiles[0].endswith(".txt"):
    print("Reading input files from %s" % params.inputFiles[0])
    with open(params.inputFiles[0].replace("file:", "")) as f:
        input_files = f.readlines()
        input_files = [x.strip() for x in input_files]
    print("Found %d input files" % len(input_files))
    del params.inputFiles[0]
    params.inputFiles = input_files
    print(params.inputFiles)
process.source = cms.Source(
    "PoolSource",
    fileNames=cms.untracked.vstring(params.inputFiles),
    secondaryFileNames=cms.untracked.vstring(),
)

process.options = cms.untracked.PSet(
    FailPath = cms.untracked.vstring(),
    IgnoreCompletely = cms.untracked.vstring(),
    Rethrow = cms.untracked.vstring(),
    SkipEvent = cms.untracked.vstring(),
    accelerators = cms.untracked.vstring('*'),
    allowUnscheduled = cms.obsolete.untracked.bool,
    canDeleteEarly = cms.untracked.vstring(),
    deleteNonConsumedUnscheduledModules = cms.untracked.bool(True),
    dumpOptions = cms.untracked.bool(False),
    emptyRunLumiMode = cms.obsolete.untracked.string,
    eventSetup = cms.untracked.PSet(
        forceNumberOfConcurrentIOVs = cms.untracked.PSet(
            allowAnyLabel_=cms.required.untracked.uint32
        ),
        numberOfConcurrentIOVs = cms.untracked.uint32(0)
    ),
    fileMode = cms.untracked.string('FULLMERGE'),
    forceEventSetupCacheClearOnNewRun = cms.untracked.bool(False),
    holdsReferencesToDeleteEarly = cms.untracked.VPSet(),
    makeTriggerResults = cms.obsolete.untracked.bool,
    modulesToIgnoreForDeleteEarly = cms.untracked.vstring(),
    numberOfConcurrentLuminosityBlocks = cms.untracked.uint32(0),
    numberOfConcurrentRuns = cms.untracked.uint32(1),
    numberOfStreams = cms.untracked.uint32(0),
    numberOfThreads = cms.untracked.uint32(1),
    printDependencies = cms.untracked.bool(False),
    sizeOfStackForThreadsInKB = cms.optional.untracked.uint32,
    throwIfIllegalParameter = cms.untracked.bool(True),
    wantSummary = cms.untracked.bool(False)
)


# Production Info
process.configurationMetadata = cms.untracked.PSet(
    annotation=cms.untracked.string("--python_filename nevts:-1"),
    name=cms.untracked.string("Applications"),
    version=cms.untracked.string("$Revision: 1.19 $"),
)

# Output definition
process.NANOAODSIMoutput = cms.OutputModule("NanoAODOutputModule",
    compressionAlgorithm=cms.untracked.string("LZMA"),
    compressionLevel=cms.untracked.int32(9),
    dataset=cms.untracked.PSet(
        dataTier=cms.untracked.string("NANOAODSIM"), filterName=cms.untracked.string("")
    ),
    fileName=cms.untracked.string(params.outputFile),
    outputCommands=process.NANOAODSIMEventContent.outputCommands,
    fakeNameForCrab=cms.untracked.bool(params.isCRAB),
    SelectEvents=cms.untracked.PSet(SelectEvents=cms.vstring("skim_step")),
)

# Additional output definition
# Other statements
from Configuration.AlCa.GlobalTag import GlobalTag

if params.era == "2022":
    process.GlobalTag = GlobalTag(process.GlobalTag, '130X_mcRun3_2022_realistic_v5', '')
elif params.era == "2022EE":
    process.GlobalTag = GlobalTag(process.GlobalTag, '130X_mcRun3_2022_realistic_postEE_v6', '')
elif params.era == "2023":
    process.GlobalTag = GlobalTag(process.GlobalTag, '130X_mcRun3_2023_realistic_v14', '')
elif params.era == "2023BPix":
    process.GlobalTag = GlobalTag(process.GlobalTag, '130X_mcRun3_2023_realistic_postBPix_v2', '')

# Keep track of the gen weights
process.genWeightSum = cms.EDProducer(
    "GenWeightsTablePreSkimProducer",
    genEvent=cms.InputTag("generator"),
    genParticles=cms.InputTag("prunedGenParticles"),
)
process.genweight_step = cms.Path(process.genWeightSum)

process.NANOAODSIMoutput.outputCommands.extend(
    [
        "keep nanoaodMergeableCounterTable_genWeightSum_*_*",
    ]
)

# HLT filter and skimmer
process.load("PhysicsTools.SUEPNano.gen_model_verifier_cff")
process.load("PhysicsTools.SUEPNano.hlt_skim_Run3_cff")
process.load("PhysicsTools.SUEPNano.muon_skim_cff")
process.skim_step = cms.Path(
    process.gen_model_verifier * process.hltHighLevel * process.muon_skim
)

# And also at the start of the nano not to run code that we don't need
process.nanoSequenceMC.insert(0, process.muon_skim)
process.nanoSequenceMC.insert(0, process.hltHighLevel)
process.nanoSequenceMC.insert(0, process.gen_model_verifier)
process.nanoSequenceMC.insert(0, process.genWeightSum)

# Path and EndPath definitions
process.nanoAOD_step = cms.Path(process.nanoSequenceMC)
process.endjob_step = cms.EndPath(process.endOfProcess)
process.NANOAODSIMoutput_step = cms.EndPath(process.NANOAODSIMoutput)

# Schedule definition
process.schedule = cms.Schedule(
    process.genweight_step,
    process.skim_step,
    process.nanoAOD_step,
    process.endjob_step,
    process.NANOAODSIMoutput_step,
)
from PhysicsTools.PatAlgos.tools.helpers import associatePatAlgosToolsTask

associatePatAlgosToolsTask(process)

# Setup FWK for multithreaded
process.options.numberOfThreads = cms.untracked.uint32(params.cpu)
process.options.numberOfStreams = cms.untracked.uint32(0)

# customisation of the process.

# Automatic addition of the customisation function from PhysicsTools.NanoAOD.nano_cff
from PhysicsTools.NanoAOD.nano_cff import nanoAOD_customizeCommon 

#call to customisation function nanoAOD_customizeCommon imported from PhysicsTools.NanoAOD.nano_cff
process = nanoAOD_customizeCommon(process)

# Automatic addition of the customisation function from PhysicsTools.SUEPNano.nano_suep_cff
from PhysicsTools.SUEPNano.nano_suep_cff import SUEPNano_customize

# call to customisation function SUEPNano_customize imported from PhysicsTools.SUEPNano.nano_suep_cff
process = SUEPNano_customize(process)

process.nanoSequenceMC.remove(process.rivetProducerHTXS)
process.nanoSequenceMC.remove(process.HTXSCategoryTable)

# End of customisation functions

# Customisation from command line
process.add_(cms.Service("InitRootHandlers", EnableIMT=cms.untracked.bool(False)))

if not params.verbose:
    process.MessageLogger.cerr.FwkReport.reportEvery = 1000

# Add early deletion of temporary data products to reduce peak memory need
from Configuration.StandardSequences.earlyDeleteSettings_cff import customiseEarlyDelete

process = customiseEarlyDelete(process)
# End adding early deletion
