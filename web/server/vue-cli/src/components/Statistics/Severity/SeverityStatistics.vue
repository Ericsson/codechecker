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

        <v-card-title class="justify-center">
          Severity statistics
          <tooltip-help-icon>
            This table shows severity statistics for the product.
            <br><br>
            The following filters don't affect these values:
            <ul>
              <li><b>Severity</b> filter.</li>
              <li><b>Source component</b> filter.</li>
            </ul>
          </tooltip-help-icon>
        </v-card-title>

        <severity-statistics-table
          :items="statistics"
          :loading="loading"
        />

        <unique-stat-warning v-if="reportFilter.isUnique" />
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <component-severity-statistics
          :bus="bus"
          :namespace="namespace"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { SeverityMixin, ToCSV } from "@/mixins";

import { BaseStatistics, UniqueStatWarning } from "@/components/Statistics";
import { ComponentSeverityStatistics } from "./ComponentSeverityStatistics";
import {
  getSeverityStatistics
} from "@/components/Statistics/StatisticsHelper";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";

import SeverityStatisticsTable from "./SeverityStatisticsTable";

export default {
  name: "SeverityStatistics",
  components: {
    SeverityStatisticsTable,
    UniqueStatWarning,
    ComponentSeverityStatistics,
    TooltipHelpIcon
  },
  mixins: [ BaseStatistics, SeverityMixin, ToCSV ],

  data() {
    return {
      loading: false,
      statistics: []
    };
  },

  methods: {
    downloadCSV() {
      const data = [
        [ "Severity", "Unreviewed", "Confirmed bug",
          "Outstanding reports (Unreviewed + Confirmed)", "False positive",
          "Intentional", "Suppressed reports (False positive + Intentional)",
          "All reports"
        ],
        ...this.statistics.map(stat => {
          return [
            this.severityFromCodeToString(stat.severity),
            stat.unreviewed.count, stat.confirmed.count,
            stat.outstanding.count, stat.falsePositive.count,
            stat.intentional.count, stat.suppressed.count, stat.reports.count
          ];
        })
      ];

      this.toCSV(data, "codechecker_severity_statistics.csv");
    },

    getStatistics: getSeverityStatistics,

    async fetchStatistics() {
      this.loading = true;

      const { runIds, reportFilter, cmpData } = this.getStatisticsFilters();
      this.statistics =
        await getSeverityStatistics(runIds, reportFilter, cmpData);

      await this.fetchDifference("severity");

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
