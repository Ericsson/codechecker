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

import {
  BaseStatistics,
  getComponents,
  initDiffField
} from "@/components/Statistics";
import {
  getComponentStatistics
} from "@/components/Statistics/StatisticsHelper";

import ComponentStatisticsTable from "./ComponentStatisticsTable";

export default {
  name: "ComponentStatistics",
  components: {
    ComponentStatisticsTable
  },
  mixins: [ BaseStatistics, ToCSV ],

  data() {
    return {
      ReviewStatus,
      loading: false,
      statistics: [],
      components: [],
      statisticsFilters: {},
      fieldsToUpdate: [ "reports", "unreviewed", "confirmed",
        "falsePositive", "intentional" ]
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
        const q1 = this.getNewReports(component).then(newReports => {
          const row = this.statistics.find(s =>
            s.component === component.name);

          if (row) {
            this.fieldsToUpdate.forEach(f => row[f].new = newReports[f].count);
            this.updateCalculatedFields(row, newReports, "new");
          }
        });

        const q2 = this.getResolvedReports(component).then(resolvedReports => {
          const row = this.statistics.find(s =>
            s.component === component.name);

          if (row) {
            this.fieldsToUpdate.forEach(f =>
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

    initStatistics(components) {
      this.statistics = components.map(component => ({
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
    },

    async getStatistics(component, runIds, reportFilter, cmpData) {
      const res = await getComponentStatistics(component, runIds, reportFilter,
        cmpData);

      return {
        component     : component.name,
        value         : component.value || component.description,
        reports       : initDiffField(res.reports),
        unreviewed    : initDiffField(res.unreviewed),
        confirmed     : initDiffField(res.confirmed),
        outstanding   : initDiffField(res.outstanding),
        falsePositive : initDiffField(res.falsePositive),
        intentional   : initDiffField(res.intentional),
        suppressed    : initDiffField(res.suppressed)
      };
    },

    async fetchStatistics() {
      this.loading = true;
      this.statistics = [];

      this.components = await getComponents();
      this.initStatistics(this.components);

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
