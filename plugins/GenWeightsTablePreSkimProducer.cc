/*
    Description: A producer to extract the generator weight from the GenEventInfoProduct and store it in the Runs tree.
    This is supposed to run at the beginning of the processing, before any skim or other processing is done.
    The weight is stored in a nanoaod::FlatTable, and the sum of weights is stored in a nanoaod::MergeableCounterTable.

    Author: Christos Papageorgakis (borrowing heavily from the GenWeightsTableProducer.cc in PhysicsTools/NanoAOD/plugins
    https://github.com/cms-sw/cmssw/blob/a54a2a91c59f52c3cb7ed96da7551a71d53745bf/PhysicsTools/NanoAOD/plugins/GenWeightsTableProducer.cc)
*/

#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/Run.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/NanoAOD/interface/MergeableCounterTable.h"
#include "SimDataFormats/GeneratorProducts/interface/GenEventInfoProduct.h"
#include "SimDataFormats/GeneratorProducts/interface/GenLumiInfoHeader.h"

#include "PhysicsTools/SUEPNano/plugins/Counters.h"

#include "boost/algorithm/string.hpp"

class GenWeightsTablePreSkimProducer : public edm::global::EDProducer<edm::StreamCache<counters::CounterMap>,
                                                                      edm::RunSummaryCache<counters::CounterMap>, 
                                                                      edm::EndRunProducer> {
    public:
        GenWeightsTablePreSkimProducer(edm::ParameterSet const& params)
        : genTag_(consumes<GenEventInfoProduct>(params.getParameter<edm::InputTag>("genEvent"))),
          genLumiInfoHeadTag_(
            mayConsume<GenLumiInfoHeader, edm::InLumi>(params.getParameter<edm::InputTag>("genLumiInfoHeader"))) {
            produces<nanoaod::FlatTable>();
            produces<std::string>("genModel");
            produces<nanoaod::MergeableCounterTable, edm::Transition::EndRun>();
        }

        ~GenWeightsTablePreSkimProducer() override {}

        // Initialize an empty counter map for the global run
        std::shared_ptr<counters::CounterMap> globalBeginRunSummary(edm::Run const&, edm::EventSetup const&) const override {
            return std::make_shared<counters::CounterMap>();
        }

        // Clear the counter map at the beginning of each run
        void streamBeginRun(edm::StreamID id, edm::Run const&, edm::EventSetup const&) const override {
            streamCache(id)->clear();
        }

        // Initialize an empty counter map for each stream
        std::unique_ptr<counters::CounterMap> beginStream(edm::StreamID) const override {
            return std::make_unique<counters::CounterMap>();
        }

        void streamBeginLuminosityBlock(edm::StreamID id,
                                        edm::LuminosityBlock const& lumiBlock,
                                        edm::EventSetup const&) const override {
            auto counterMap = streamCache(id);
            edm::Handle<GenLumiInfoHeader> genLumiInfoHead;
            lumiBlock.getByToken(genLumiInfoHeadTag_, genLumiInfoHead);

            std::string label;
            if (genLumiInfoHead.isValid()) {
                label = genLumiInfoHead->configDescription();
                boost::replace_all(label, "-", "_");
                boost::replace_all(label, "/", "_");
            }
            counterMap->setLabel(label);
        }

        // Produce the generator weight and store it in the stream counter map
        void produce(edm::StreamID id, edm::Event& iEvent, const edm::EventSetup& iSetup) const override {
            counters::Counter* counter = streamCache(id)->get();

            edm::Handle<GenEventInfoProduct> genInfo;
            iEvent.getByToken(genTag_, genInfo);
            double weight = genInfo->weight();

            auto out = std::make_unique<nanoaod::FlatTable>(1, "genWeight", true);
            out->setDoc("generator weight");
            out->addColumnValue<float>("", weight, "generator weight", nanoaod::FlatTable::FloatColumn);
            
            std::string model_label = streamCache(id)->getLabel();
            auto outM = std::make_unique<std::string>((!model_label.empty()) ? std::string("GenModel_") + model_label : "");
            iEvent.put(std::move(outM), "genModel");
            
            counter->incGenOnly(weight);
            
            iEvent.put(std::move(out));
        }

        // Merge the stream counter map into the global counter map
        void streamEndRunSummary(
            edm::StreamID id,
            edm::Run const& run,
            edm::EventSetup const&,
            counters::CounterMap* runCounterMap
        ) const override {
            runCounterMap->merge(*streamCache(id));
        }

        void globalEndRunSummary(edm::Run const& run, edm::EventSetup const&, counters::CounterMap* runCounterMap) const override {}

        // Produce the sum of weights in the global run
        void globalEndRunProduce(edm::Run& iRun, edm::EventSetup const&, counters::CounterMap const* runCounterMap) const override {
            auto out = std::make_unique<nanoaod::MergeableCounterTable>();

            for (const auto& x : runCounterMap->countermap) {
                auto runCounter = &(x.second);
                std::string label = (!x.first.empty()) ? (std::string("_") + x.first) : "";
                std::string doclabel = (!x.first.empty()) ? (std::string(", for model label ") + x.first) : "";

                out->addInt("genEventCountPreSkim" + label, "event count" + doclabel, runCounter->num);
                out->addFloat("genEventSumwPreSkim" + label, "sum of gen weights" + doclabel, runCounter->sumw);
                out->addFloat("genEventSumw2PreSkim" + label, "sum of gen (weight^2)" + doclabel, runCounter->sumw2);
            }
            iRun.put(std::move(out));
        }

        static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
            edm::ParameterSetDescription desc;
            desc.add<edm::InputTag>("genEvent", edm::InputTag("generator"))
                ->setComment("tag for the GenEventInfoProduct, to get the main weight");
            desc.add<edm::InputTag>("genLumiInfoHeader", edm::InputTag("generator"))
                ->setComment("tag for the GenLumiInfoProduct, to get the model string");
            descriptions.add("genWeights", desc);
        }

    protected:
        const edm::EDGetTokenT<GenEventInfoProduct> genTag_;
        const edm::EDGetTokenT<GenLumiInfoHeader> genLumiInfoHeadTag_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(GenWeightsTablePreSkimProducer);
