import { mapMutations, mapState } from "vuex";
import {
  SET_CMP_DATA,
  SET_REPORT_FILTER,
  SET_RUN_IDS
} from "@/store/mutations.type";

import { ReportFilter } from "@cc/report-server-types";

export default {
  name: "BaseFilterMixin",

  props: {
    namespace: { type: String, required: true }
  },

  computed: {
    ...mapState({
      runIds(state) {
        return state[this.namespace].runIds;
      },
      reportFilter(state) {
        return state[this.namespace].reportFilter;
      },
      cmpData(state) {
        return state[this.namespace].cmpData;
      }
    }),

    reportFilterModel() {
      return new ReportFilter(this.reportFilter);
    },
    runIdsModel() {
      return this.runIds ? this.runIds.slice(0) : null;
    }
  },

  methods: {
    ...mapMutations({
      [SET_RUN_IDS](commit, payload) {
        return commit(`${this.namespace}/${SET_RUN_IDS}`, payload);
      },
      [SET_REPORT_FILTER](commit, payload) {
        return commit(`${this.namespace}/${SET_REPORT_FILTER}`, payload);
      },
      [SET_CMP_DATA](commit, payload) {
        return commit(`${this.namespace}/${SET_CMP_DATA}`, payload);
      }
    }),

    getUrlState() {
      return {};
    },

    initByUrl() {
      return new Promise(resolve => { resolve(); });
    },

    // When mutating (rather than replacing) an Object or an Array, the old
    // value will be the same as new value because they reference the same
    // Object/Array. For this reason we are using computed property for
    // ReportFilter to get the old values and see what are the changes.
    registerWatchers() {
      this.unregisterWatchers();

      this.reportFilterUnwatch = this.$watch("reportFilterModel",
        (oldVal, newVal) => {
          Object.keys(newVal).forEach(key => {
            if (JSON.stringify(newVal[key]) !== JSON.stringify(oldVal[key])) {
              this.onReportFilterChange(key, oldVal, newVal);
            }
          });
        }, { deep: true });

      this.runIdsUnwatch = this.$watch("runIdsModel", (oldVal, newVal) => {
        this.onRunIdsChange(oldVal, newVal);
      });
    },

    unregisterWatchers() {
      if (this.reportFilterUnwatch) this.reportFilterUnwatch();
      if (this.runIdsUnwatch) this.runIdsUnwatch();
    },

    beforeInit() {
      this.unregisterWatchers();

      this.setRunIds([]);
      this.setReportFilter(new ReportFilter());
      this.setCmpData(null);
    },

    afterInit() {
      this.registerWatchers();
    },

    updateUrl() {
      const state = this.getUrlState();
      const queryParams = Object.assign({}, this.$route.query, state);
      this.$router.replace({ query: queryParams }).catch(() => {});
    },

    updateReportFilter() {},

    fetchItems() {},

    clear() {},

    onRunIdsChange(/* oldVal, newVal */) {
      this.fetchItems();
    },

    onReportFilterChange(/* key, oldValue, newValue */) {
      this.fetchItems();
    },
  }
};
