<template>
  <v-container fluid>
    <v-row>
      <v-col cols="auto">
        <h3 class="title primary--text">
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

        <severity-statistics-table
          :items="statistics"
          :loading="loading"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { SeverityMixin, ToCSV } from "@/mixins";

import BaseStatistics from "./BaseStatistics";
import SeverityStatisticsTable from "./SeverityStatisticsTable";
import { initDiffField, resultToNumber } from "./StatisticsHelper";

export default {
  name: "SeverityStatistics",
  components: {
    SeverityStatisticsTable
  },
  mixins: [ BaseStatistics, SeverityMixin, ToCSV ],

  props: {
    namespace: { type: String, required: true }
  },

  data() {
    return {
      loading: false,
      statistics: []
    };
  },

  methods: {
    downloadCSV() {
      const data = [
        [ "Severity", "Reports" ],
        ...this.statistics.map(stat => {
          return [
            this.severityFromCodeToString(stat.severity),
            stat.reports.toNumber()
          ];
        })
      ];

      this.toCSV(data, "codechecker_severity_statistics.csv");
    },

    getStatistics(runIds, reportFilter, cmpData) {
      return new Promise(resolve => {
        ccService.getClient().getSeverityCounts(runIds, reportFilter, cmpData,
          handleThriftError(statistics => resolve(statistics)));
      });
    },

    /**
     * If compare data is set this function will get the number of new and
     * resolved bugs and update the statistics.
     */
    async fetchDifference() {
      if (!this.cmpData) return;

      const q1 = this.getNewReports().then(newReports => {
        this.statistics.forEach(s => {
          s.reports.new = resultToNumber(newReports[s.severity]);
        });
      });

      const q2 = this.getResolvedReports().then(resolvedReports => {
        this.statistics.forEach(s => {
          s.reports.resolved = resultToNumber(resolvedReports[s.severity]);
        });
      });

      return Promise.all([ q1, q2 ]);
    },

    async fetchStatistics() {
      this.loading = true;

      const { runIds, reportFilter, cmpData } = this.getStatisticsFilters();
      const statistics =
        await this.getStatistics(runIds, reportFilter, cmpData);

      this.statistics = Object.keys(statistics).map(severity => {
        return {
          severity: parseInt(severity),
          reports: initDiffField(statistics[severity])
        };
      });

      await this.fetchDifference();

      this.loading = false;
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .severity {
  text-decoration: none;
}
</style>
