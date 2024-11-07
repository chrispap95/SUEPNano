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

#include "PhysicsTools/SUEPNano/plugins/Counters.h"

#include <iostream>
#include <atomic>
#include <memory>


class GenWeightProducer : public edm::global::EDProducer<edm::StreamCache<CounterMap>,
                                                        edm::RunSummaryCache<CounterMap>, 
                                                        edm::EndRunProducer> {
    public:
        explicit GenWeightProducer(edm::ParameterSet const& params)
        : genTag_(consumes<GenEventInfoProduct>(params.getParameter<edm::InputTag>("genEventInfo"))) {
            produces<nanoaod::FlatTable>();
            produces<nanoaod::MergeableCounterTable, edm::Transition::EndRun>();
        }

        ~GenWeightProducer() override {}

        // Initialize an empty counter map for each stream
        std::unique_ptr<CounterMap> beginStream(edm::StreamID id) const override {
            return std::make_unique<CounterMap>();
        }

        // Produce the generator weight and store it in the stream counter map
        void produce(edm::StreamID id, edm::Event& iEvent, const edm::EventSetup& iSetup) const override {
            edm::Handle<GenEventInfoProduct> genInfo;
            iEvent.getByToken(genTag_, genInfo);

            if (!genInfo.isValid()) {
                edm::LogError("GenWeightProducer") << "Failed to get GenEventInfoProduct";
                return;
            }

            double weight = genInfo->weight();

            auto& counter = streamCache(id)->countermap[""];
            counter.incGenOnly(weight);

            auto out = std::make_unique<nanoaod::FlatTable>(1, "genWeight", true);
            out->setDoc("generator weight");
            out->addColumnValue<float>("", weight, "generator weight", nanoaod::FlatTable::FloatColumn);
            iEvent.put(std::move(out));
        }

        // Clear the counter map at the beginning of each run
        void streamBeginRun(edm::StreamID id, edm::Run const& run, edm::EventSetup const&) const override {
            streamCache(id)->clear();
        }

        // Initialize an empty counter map for the global run
        std::shared_ptr<CounterMap> globalBeginRunSummary(edm::Run const& run, edm::EventSetup const&) const override {
            return std::make_shared<CounterMap>();
        }

        // Merge the stream counter map into the global counter map
        void streamEndRunSummary(
            edm::StreamID id,
            edm::Run const& run,
            edm::EventSetup const&,
            CounterMap* runCounterMap
        ) const override {
            runCounterMap->merge(*streamCache(id));
        }

        void globalEndRunSummary(edm::Run const& run, edm::EventSetup const&, CounterMap* runCounterMap) const override {}

        // Produce the sum of weights in the global run
        void globalEndRunProduce(edm::Run& iRun, edm::EventSetup const&, CounterMap const* runCounterMap) const override {
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
            desc.add<edm::InputTag>("genEventInfo", edm::InputTag("generator"))
                ->setComment("tag for the GenEventInfoProduct, to get the main weight");
            descriptions.add("genWeightsTable", desc);
        }

    protected:
        const edm::EDGetTokenT<GenEventInfoProduct> genTag_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(GenWeightProducer);
