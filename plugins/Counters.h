/*
    This code was taken almost as is from GenWeightsTableProducer.cc in PhysicsTools/NanoAOD/plugins
    https://github.com/cms-sw/cmssw/blob/a54a2a91c59f52c3cb7ed96da7551a71d53745bf/PhysicsTools/NanoAOD/plugins/GenWeightsTableProducer.cc
*/

#ifndef PhysicsTools_SUEPNano_Counters_h
#define PhysicsTools_SUEPNano_Counters_h

namespace counters {
    ///  ---- Cache object for running sums of weights ----
    struct Counter {
        Counter() : num(0), sumw(0), sumw2(0) {}

        // the counters
        long long num;
        long double sumw;
        long double sumw2;

        void clear() {
            num = 0;
            sumw = 0;
            sumw2 = 0;
        }

        // inc the counters
        void incGenOnly(double w) {
            num++;
            sumw += w;
            sumw2 += (w * w);
        }

        void merge(const Counter& other) {
            num += other.num;
            sumw += other.sumw;
            sumw2 += other.sumw2;
        }
    };

    struct CounterMap {
        std::map<std::string, Counter> countermap;
        Counter* active_el = nullptr;
        std::string active_label = "";
        void merge(const CounterMap& other) {
            for (const auto& y : other.countermap)
                countermap[y.first].merge(y.second);
            active_el = nullptr;
        }
        void clear() {
            for (auto x : countermap)
                x.second.clear();
            active_el = nullptr;
            active_label = "";
        }
        void setLabel(std::string label) {
            active_el = &(countermap[label]);
            active_label = label;
        }
        void checkLabelSet() {
            if (!active_el)
                throw cms::Exception("LogicError", "Called CounterMap::get() before setting the active label\n");
        }
        Counter* get() {
            checkLabelSet();
            return active_el;
        }
        std::string& getLabel() {
            checkLabelSet();
            return active_label;
        }
    };
}  // namespace

#endif
