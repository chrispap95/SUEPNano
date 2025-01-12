/*
  Description: Skim events for at least 3 muons that pass the cleaning selections: 
  pt, leading muon pt, eta, dxy, dz, and isMediumMuon

  Author: Christos Papageorgakis
*/

#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/global/EDFilter.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "DataFormats/PatCandidates/interface/Muon.h"

#include <vector>
#include <iostream>


class Muon_Skim : public edm::global::EDFilter<> {
  public:
    explicit Muon_Skim(const edm::ParameterSet&);
    ~Muon_Skim() override = default;
    bool filter(edm::StreamID, edm::Event& iEvent, const edm::EventSetup&) const override;
    static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

  private:
    // ----------member data ---------------------------
    edm::EDGetTokenT<std::vector<pat::Muon>> muonInput;
    double mu_minpt_;
    double mu_etacut_;
    double mu_dxy_;
    double mu_dz_;
    double leadmu_pt_;
};

// constructors and destructor
Muon_Skim::Muon_Skim(const edm::ParameterSet& iConfig)
{
   //now do what ever initialization is needed
  muonInput   = consumes<std::vector<pat::Muon>>(iConfig.getParameter<edm::InputTag>("srcmuons"));
  mu_minpt_   = iConfig.getParameter<double>("mu_minpt");
  mu_etacut_  = iConfig.getParameter<double>("mu_maxeta");
  mu_dxy_     = iConfig.getParameter<double>("mu_dxy");
  mu_dz_      = iConfig.getParameter<double>("mu_dz");
  leadmu_pt_ = iConfig.getParameter<double>("leadmu_pt"); 
}

// ------------ method called on each new Event  ------------
bool Muon_Skim::filter(edm::StreamID, edm::Event& iEvent, const edm::EventSetup&) const
{
  // Get muons
  edm::Handle<std::vector<pat::Muon>> muons;
  iEvent.getByToken(muonInput, muons);

  // All relevant flags
  bool isGoodLeading = false;
  bool enoughMuons = false;
  int nMuons = 0;

  // Loop over muons
  if(muons.isValid()){
    for (std::vector<pat::Muon>::const_iterator itmuon=muons->begin(); itmuon!=muons->end(); ++itmuon){
      if(
        abs(itmuon->eta()) < mu_etacut_ && 
        itmuon->pt() > mu_minpt_ && 
        abs(itmuon->dB(pat::Muon::IPTYPE::PV2D)) < mu_dxy_ && 
        abs(itmuon->dB(pat::Muon::IPTYPE::PVDZ)) < mu_dz_ &&
        itmuon->isMediumMuon()
      ){
	      nMuons += 1;
        if (itmuon->pt() > leadmu_pt_) isGoodLeading = true;
      }
    }
  }

  if (nMuons > 2) enoughMuons = true;

  return enoughMuons && isGoodLeading;
}

// ------------ method fills 'descriptions' with the allowed parameters for the module  ------------
void Muon_Skim::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.setUnknown();
  descriptions.addDefault(desc);
}

//define this as a plug-in
DEFINE_FWK_MODULE(Muon_Skim);
