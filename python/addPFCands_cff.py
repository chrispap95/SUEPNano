import FWCore.ParameterSet.Config as cms
from  PhysicsTools.NanoAOD.common_cff import *

def addPFCands(process):
    process.customizedPFCandsTask = cms.Task()
    process.schedule.associate(process.customizedPFCandsTask)
    candInput = cms.InputTag("packedPFCandidates")

    process.customConstituentsExtTable = cms.EDProducer("SimpleCandidateFlatTableProducer",
                                                        src = candInput,
                                                        cut = cms.string(""), 
                                                        name = cms.string("PFCands"),
                                                        doc = cms.string("PF candidates"),
                                                        singleton = cms.bool(False), 
                                                        extension = cms.bool(False), 
                                                        variables = cms.PSet(CandVars,
                                                            puppiWeight = Var("puppiWeight()", float, doc="Puppi weight",precision=10),
                                                            puppiWeightNoLep = Var("puppiWeightNoLep()", float, doc="Puppi weight removing leptons",precision=10),
                                                            vtxChi2 = Var("?hasTrackDetails()?vertexChi2():-1", float, doc="vertex chi2",precision=10),
                                                            trkChi2 = Var("?hasTrackDetails()?pseudoTrack().normalizedChi2():-1", float, doc="normalized trk chi2", precision=10),
                                                            dz = Var("?hasTrackDetails()?dz():-1", float, doc="pf dz", precision=10),
                                                            dzErr = Var("?hasTrackDetails()?dzError():-1", float, doc="pf dz err", precision=10),
                                                            d0 = Var("?hasTrackDetails()?dxy():-1", float, doc="pf d0", precision=10),
                                                            d0Err = Var("?hasTrackDetails()?dxyError():-1", float, doc="pf d0 err", precision=10),
                                                            pvAssocQuality = Var("pvAssociationQuality()", int, doc="primary vertex association quality"),
                                                            lostInnerHits = Var("lostInnerHits()", int, doc="lost inner hits"),
                                                            trkQuality = Var("?hasTrackDetails()?pseudoTrack().qualityMask():0", int, doc="track quality mask"),
                                                            trkPt = Var("?hasTrackDetails()?sqrt(pseudoTrack().momentum().Perp2()):0", float, doc="track transverse momentum", precision=10),
                                                            trkEta = Var("?hasTrackDetails()?sqrt(pseudoTrack().momentum().Eta()):-99", float, doc="track pseudorapidity", precision=10),
                                                            trkPhi = Var("?hasTrackDetails()?sqrt(pseudoTrack().momentum().Phi()):-99", float, doc="track azimuthal angle", precision=10),
                                                        )
                                            )

    process.customizedPFCandsTask.add(process.customConstituentsExtTable)

    return process
