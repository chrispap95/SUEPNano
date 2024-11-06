# Description: HLT skim for TripleMu triggers

import FWCore.ParameterSet.Config as cms

hltHighLevel = cms.EDFilter(
    "HLTHighLevel",
    TriggerResultsTag=cms.InputTag("TriggerResults", "", "HLT"),
    HLTPaths=cms.vstring(
        "HLT_TripleMu_12_10_5_v*",
        "HLT_TripleMu_5_3_3_DZ_Mass3p8_v*",
        "HLT_TripleMu_5_3_3_v*",
    ),
    eventSetupPathsKey=cms.string(""),
    andOr=cms.bool(True),  # True (OR) accept if ANY is true
    throw=cms.bool(False),  # do not throw exception on unknown path names
)
