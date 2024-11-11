<script>
import { mapState } from "vuex";
import { CompareData, DiffType, ReportFilter } from "@cc/report-server-types";

export default {
  name: "BaseStatistics",
  props: {
    bus: { type: Object, required: true },
    namespace: { type: String, required: true }
  },
  data() {
    return {
      statistics: []
    };
  },

  computed: {
    ...mapState({
      runIds(state, getters) {
        return getters[`${this.namespace}/getRunIds`];
      },
      reportFilter(state, getters) {
        return getters[`${this.namespace}/getReportFilter`];
      },
      cmpData(state, getters) {
        return getters[`${this.namespace}/getCmpData`];
      }
    })
  },

  activated() {
    this.bus.$on("refresh", this.fetchStatistics);
  },

  deactivated() {
    this.bus.$off("refresh", this.fetchStatistics);
  },

  mounted() {
    // The fetchStatistics function which initalizes this component is called
    // dynamically by the parent component. If Hot Module Replacement is
    // enabled and this component will be replaced then this initialization
    // will not be made. For this reason on component replacement we will save
    // the data and we will initalize the new component with this data.
    if (process.env.NODE_ENV !== "production") {
      if (module.hot) {
        if (module.hot.data) {
          this.statistics = module.hot.data.statistics;
        }

        module.hot.dispose(data => data["statistics"] = this.statistics);
      }
    }
  },

  methods: {
    fetchStatistics() {},

    updateCalculatedFields(oldValues, newValues, type) {
      if (oldValues["outstanding"] !== undefined) {
        oldValues["outstanding"][type] =
          newValues["unreviewed"].count + newValues["confirmed"].count;
      }

      if (oldValues["suppressed"] !== undefined) {
        oldValues["suppressed"][type] =
          newValues["falsePositive"].count + newValues["intentional"].count;
      }
    },

    updateStatistics(reports, name, type) {
      const fieldToUpdate = [ "reports", "unreviewed", "confirmed",
        "falsePositive", "intentional" ];

      this.statistics.forEach(s => {
        const row = reports.find(n => n[name] === s[name]);
        if (row) {
          fieldToUpdate.forEach(f => s[f][type] = row[f].count);
          this.updateCalculatedFields(s, row, type);
        }
      });
    },

    /**
     * If compare data is set this function will get the number of new and
     * resolved bugs and update the statistics.
     */
    async fetchDifference(name) {
      if (!this.cmpData) return;

      const q1 = this.getNewReports().then(newReports => {
        this.updateStatistics(newReports, name, "new");
      });

      const q2 = this.getResolvedReports().then(resolvedReports => {
        this.updateStatistics(resolvedReports, name, "resolved");
      });

      return Promise.all([ q1, q2 ]);
    },

    getStatistics(/* runIds, reportFilter, cmpData */) {},

    getNewReports() {
      const runIds = this.runIds;
      const reportFilter = this.reportFilter;
      const cmpData = new CompareData(this.cmpData);
      cmpData.diffType = DiffType.NEW;

      return this.getStatistics(runIds, reportFilter, cmpData);
    },

    getResolvedReports() {
      const runIds = this.runIds;
      const reportFilter = this.reportFilter;
      const cmpData = new CompareData(this.cmpData);
      cmpData.diffType = DiffType.RESOLVED;

      return this.getStatistics(runIds, reportFilter, cmpData);
    },

    getStatisticsFilters() {
      let runIds = this.runIds;
      let reportFilter = this.reportFilter;
      const cmpData = null;

      // If compare data is set, get statistics for the compared to data.
      if (this.cmpData) {
        runIds = this.cmpData.runIds;
        reportFilter = new ReportFilter(this.reportFilter);
        reportFilter.runTag = this.cmpData.runTag;
      }

      return {
        runIds,
        reportFilter,
        cmpData
      };
    }
  }
};
</script>