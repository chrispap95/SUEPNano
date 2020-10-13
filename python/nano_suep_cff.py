import FWCore.ParameterSet.Config as cms

from PhysicsTools.SUEPNano.addPFCands_cff import addPFCands
from PhysicsTools.NanoAOD.common_cff import Var


def SUEPNano_customize(process):
    addPFCands(process)
    return process

