import FWCore.ParameterSet.Config as cms

muon_skim = cms.EDFilter("Muon_Skim",
    srcmuons = cms.InputTag("slimmedMuons"),
    mu_minpt = cms.double(3),
    mu_maxeta = cms.double(2.5),
    mu_dxy = cms.double(0.2),
    mu_dz = cms.double(0.2),
    leadmu_pt = cms.double(5)
)
