import { mapMutations, mapState } from "vuex";
import {
  SET_RUN_IDS,
  SET_REPORT_FILTER,
  SET_CMP_DATA
} from "@/store/mutations.type";

import { ReportFilter } from "@cc/report-server-types";

export default {
  name: "BaseFilterMixin",

  computed: {
    ...mapState({
      runIds: state => state.report.runIds,
      reportFilter: state => state.report.reportFilter,
      cmpData: state => state.report.cmpData,
    }),

    reportFilterModel() {
      return new ReportFilter(this.reportFilter);
    },
    runIdsModel() {
      return this.runIds ? this.runIds.slice(0) : null;
    }
  },

  methods: {
    ...mapMutations([
      SET_RUN_IDS,
      SET_REPORT_FILTER,
      SET_CMP_DATA
    ]),

    getUrlState() {
      return {};
    },

    initByUrl() {
      return new Promise((resolve) => { resolve(); });
    },

    // When mutating (rather than replacing) an Object or an Array, the old
    // value will be the same as new value because they reference the same
    // Object/Array. For this reason we are using computed property for
    // ReportFilter to get the old values and see what are the changes.
    registerWatchers() {
      if (this.reportFilterUnwatch) this.reportFilterUnwatch();
      this.reportFilterUnwatch = this.$watch("reportFilterModel",
      (oldVal, newVal) => {
        Object.keys(newVal).forEach((key) => {
          if (JSON.stringify(newVal[key]) !== JSON.stringify(oldVal[key])) {
            this.onReportFilterChange(key, oldVal, newVal);
          }
        });
      }, { deep: true });

      if (this.runIdsUnwatch) this.runIdsUnwatch();
      this.runIdsUnwatch = this.$watch("runIdsModel", (oldVal, newVal) => {
        this.onRunIdsChange(oldVal, newVal);
      });
    },

    afterUrlInit() {
      this.registerWatchers();
    },

    updateUrl() {
      const state = this.getUrlState();
      const queryParams = Object.assign({}, this.$route.query, state);
      this.$router.replace({ query: queryParams }).catch(() => {});
    },

    updateReportFilter() {},

    fetchItems() {},

    onRunIdsChange(/* oldVal, newVal */) {
      this.fetchItems();
    },

    onReportFilterChange(/* key, oldValue, newValue */) {
      this.fetchItems();
    },
  }
}
