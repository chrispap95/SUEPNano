import FWCore.ParameterSet.Config as cms

gen_model_verifier = cms.EDFilter(
    "GenModelVerifier",
    genParticles=cms.InputTag("prunedGenParticles"),
    genLumiInfoHeader=cms.InputTag("generator"),
)
