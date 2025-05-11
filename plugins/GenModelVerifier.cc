/*
  Description: Verifies that the generaed model has the expected mS
  This fixes the issue with RandomizedParameters not setting the correct
  mS in Pythia.

  Author: Christos Papageorgakis
*/

#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/global/EDFilter.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "SimDataFormats/GeneratorProducts/interface/GenLumiInfoHeader.h"

#include <iostream>
#include <vector>
#include <iostream>
#include <regex>
#include <string>

#include "boost/algorithm/string.hpp"

struct NoCache {};

class GenModelVerifier : public edm::global::EDFilter<edm::LuminosityBlockCache<NoCache>> {
  public:
    explicit GenModelVerifier(const edm::ParameterSet&);
    ~GenModelVerifier() override = default;
    std::shared_ptr<NoCache> globalBeginLuminosityBlock(edm::LuminosityBlock const&, edm::EventSetup const&) const override;
    void globalEndLuminosityBlock(edm::LuminosityBlock const&, edm::EventSetup const&) const override {};
    bool filter(edm::StreamID, edm::Event& iEvent, const edm::EventSetup&) const override;
    static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

  private:
    // ----------member data ---------------------------
    edm::EDGetTokenT<std::vector<reco::GenParticle>> genParticlesTag_;
    edm::EDGetTokenT<GenLumiInfoHeader> genLumiInfoHeadTag_;
    mutable std::string label_ = "";
};

// constructors and destructor
GenModelVerifier::GenModelVerifier(const edm::ParameterSet& iConfig)
{
    //now do what ever initialization is needed
    genParticlesTag_ = consumes<std::vector<reco::GenParticle>>(iConfig.getParameter<edm::InputTag>("genParticles"));
    genLumiInfoHeadTag_ = consumes<GenLumiInfoHeader, edm::InLumi>(iConfig.getParameter<edm::InputTag>("genLumiInfoHeader"));
}

std::shared_ptr<NoCache> GenModelVerifier::globalBeginLuminosityBlock(edm::LuminosityBlock const& lumiBlock, edm::EventSetup const&) const {
    edm::Handle<GenLumiInfoHeader> genLumiInfoHead;
    lumiBlock.getByToken(genLumiInfoHeadTag_, genLumiInfoHead);

    if (genLumiInfoHead.isValid()) {
        label_ = genLumiInfoHead->configDescription();
        boost::replace_all(label_, "-", "_");
        boost::replace_all(label_, "/", "_");
    } else {
        label_ = "";
    }

    return std::make_shared<NoCache>();
}

// ------------ method called on each new Event  ------------
bool GenModelVerifier::filter(edm::StreamID, edm::Event& iEvent, const edm::EventSetup&) const
{
    // Extract the mS value from the model label
    std::regex pattern("mS([0-9]+\\.[0-9]+)");
    std::smatch match;
    double mS_value = 0.0;
    if (std::regex_search(label_, match, pattern)) {
        std::string value = match[1]; // Extract the matched number as a string
        mS_value = std::stod(value); // Convert to double if needed
    } else {
        return true;
    }

    edm::Handle<std::vector<reco::GenParticle>> genParticles;
    iEvent.getByToken(genParticlesTag_, genParticles);

    if (genParticles.isValid()) {
        for (const auto& particle : *genParticles) {
            if ((particle.pdgId() == 25) && (particle.status() == 62)) {
                if (abs(particle.mass() - mS_value) / mS_value > 0.004) return false;
            }
        }
    }

    return true;
}

// ------------ method fills 'descriptions' with the allowed parameters for the module  ------------
void GenModelVerifier::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.setUnknown();
    descriptions.addDefault(desc);
}

//define this as a plug-in
DEFINE_FWK_MODULE(GenModelVerifier);
