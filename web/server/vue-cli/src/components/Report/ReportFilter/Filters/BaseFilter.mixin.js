import { mapMutations, mapState } from "vuex";
import {
  SET_CMP_DATA,
  SET_REPORT_FILTER,
  SET_RUN_IDS
} from "@/store/mutations.type";

import { CompareData, ReportFilter } from "@cc/report-server-types";

export default {
  name: "BaseFilterMixin",

  data() {
    return {
      defaultLimit: 10,
      panel: false
    };
  },

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
    },
    cmpDataModel() {
      return this.cmpData ? new CompareData(this.cmpData) : null;
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

      this.cmpDataUnwatch = this.$watch("cmpDataModel",
        (newVal, oldVal) => {
          if (!newVal || !oldVal) {
            return this.onCmpDataChange(null, oldVal, newVal);
          }

          Object.keys(newVal).forEach(key => {
            if (JSON.stringify(newVal[key]) !== JSON.stringify(oldVal[key])) {
              return this.onCmpDataChange(key, oldVal, newVal);
            }
          });
        }, { deep: true });
    },

    unregisterWatchers() {
      if (this.reportFilterUnwatch) this.reportFilterUnwatch();
      if (this.runIdsUnwatch) this.runIdsUnwatch();
      if (this.cmpDataUnwatch) this.cmpDataUnwatch();
    },

    beforeInit() {
      this.unregisterWatchers();

      this.setRunIds([]);
      this.setReportFilter(new ReportFilter());
      this.setCmpData(null);
    },

    afterInit() {
      this.registerWatchers();
      this.initPanel();
    },

    initPanel() {},

    updateReportFilter() {},

    fetchItems(/* {  limit  } */) { return []; },

    clear(/* updateUrl */) {},

    update() {},

    onRunIdsChange(/* oldVal, newVal */) {},

    onReportFilterChange(/* key, oldValue, newValue */) {},

    onCmpDataChange(/* key, oldValue, newValue */) {},
  }
};
