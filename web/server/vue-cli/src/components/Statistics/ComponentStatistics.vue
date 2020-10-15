<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h3 class="title primary--text mb-2">
          <v-btn
            color="primary"
            outlined
            @click="downloadCSV"
          >
            Export CSV
          </v-btn>

          <v-btn
            icon
            title="Reload statistics"
            color="primary"
            @click="fetchStatistics"
          >
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </h3>

        <component-statistics-table
          :items="statistics"
          :loading="loading"
          :filters="statisticsFilters"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import {
  CompareData,
  DiffType,
  ReportFilter,
  ReviewStatus
} from "@cc/report-server-types";
import { ToCSV } from "@/mixins";

import BaseStatistics from "./BaseStatistics";
import ComponentStatisticsTable from "./ComponentStatisticsTable";
import {
  getComponentStatistics,
  getComponents,
  initDiffField
} from "./StatisticsHelper";

export default {
  name: "ComponentStatistics",
  components: {
    ComponentStatisticsTable
  },
  mixins: [ BaseStatistics, ToCSV ],

  props: {
    namespace: { type: String, required: true }
  },

  data() {
    return {
      ReviewStatus,
      loading: false,
      statistics: [],
      components: [],
      statisticsFilters: {}
    };
  },

  methods: {
    downloadCSV() {
      const data = [
        [
          "Component", "Unreviewed", "Confirmed bug",
          "Outstanding reports (Unreviewed + Confirmed)", "False positive",
          "Intentional", "Suppressed reports (False positive + Intentional)",
          "All reports"
        ],
        ...this.statistics.map(stat => {
          return [
            stat.component, stat.unreviewed.count, stat.confirmed.count,
            stat.outstanding.count, stat.falsePositive.count,
            stat.intentional.count, stat.suppressed.count, stat.reports.count
          ];
        })
      ];

      this.toCSV(data, "codechecker_component_statistics.csv");
    },

    /**
     * If compare data is set this function will get the number of new and
     * resolved bugs and update the statistics.
     */
    async fetchDifference() {
      if (!this.cmpData) return;

      return Promise.all(this.components.map(component => {
        const fieldToUpdate = [ "reports", "unreviewed", "confirmed",
          "falsePositive", "intentional" ];

        const q1 = this.getNewReports(component).then(newReports => {
          const row = this.statistics.find(s =>
            s.component === component.name);

          if (row) {
            fieldToUpdate.forEach(f => row[f].new = newReports[f].count);
            this.updateCalculatedFields(row, newReports, "new");
          }
        });

        const q2 = this.getResolvedReports(component).then(resolvedReports => {
          const row = this.statistics.find(s =>
            s.component === component.name);

          if (row) {
            fieldToUpdate.forEach(f =>
              row[f].resolved = resolvedReports[f].count);
            this.updateCalculatedFields(row, resolvedReports, "resolved");
          }
        });

        return Promise.all([ q1, q2 ]);
      }));
    },

    getNewReports(component) {
      const runIds = this.runIds;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter["componentNames"] = [ component.name ];

      const cmpData = new CompareData(this.cmpData);
      cmpData.diffType = DiffType.NEW;

      return this.getStatistics(component, runIds, reportFilter, cmpData);
    },

    getResolvedReports(component) {
      const runIds = this.runIds;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter["componentNames"] = [ component.name ];

      const cmpData = new CompareData(this.cmpData);
      cmpData.diffType = DiffType.RESOLVED;

      return this.getStatistics(component, runIds, reportFilter, cmpData);
    },

    async getStatistics(component, runIds, reportFilter, cmpData) {
      const res = await getComponentStatistics(component, runIds, reportFilter,
        cmpData);

      return {
        component     : component.name,
        value         : component.value || component.description,
        reports       : initDiffField(res[0]),
        unreviewed    : initDiffField(res[1]),
        confirmed     : initDiffField(res[2]),
        outstanding   : initDiffField(res[1].toNumber() + res[2].toNumber()),
        falsePositive : initDiffField(res[3]),
        intentional   : initDiffField(res[4]),
        suppressed    : initDiffField(res[3].toNumber() + res[4].toNumber())
      };
    },

    async fetchStatistics() {
      this.loading = true;
      this.statistics = [];

      this.components = await getComponents();

      this.statistics = this.components.map(component => ({
        component     : component.name,
        value         : component.value || component.description,
        reports       : initDiffField(undefined),
        unreviewed    : initDiffField(undefined),
        confirmed     : initDiffField(undefined),
        outstanding   : initDiffField(undefined),
        falsePositive : initDiffField(undefined),
        intentional   : initDiffField(undefined),
        suppressed    : initDiffField(undefined)
      }));

      this.statisticsFilters = this.getStatisticsFilters();
      const { runIds, reportFilter, cmpData } = this.statisticsFilters;

      const queries = this.components.map(async component => {
        const res = await this.getStatistics(component, runIds, reportFilter,
          cmpData);

        const idx = this.statistics.findIndex(s =>
          s.component === component.name);

        this.statistics[idx] = {
          ...res,
          loading       : false,
          checkerStatistics: null
        };

        this.statistics = [ ...this.statistics ];

        return this.statistics[idx];
      });

      await Promise.all(queries).then(statistics =>
        this.statistics = statistics);

      await this.fetchDifference();

      this.loading = false;
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .v-data-table__expanded__content .v-card {
  padding: 10px;
}
</style>
