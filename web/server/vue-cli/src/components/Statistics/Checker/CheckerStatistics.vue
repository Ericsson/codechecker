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

        <checker-statistics-table
          :items="statistics"
          :loading="loading"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ReviewStatusMixin, SeverityMixin, ToCSV } from "@/mixins";
import { BaseStatistics } from "@/components/Statistics";
import {
  getCheckerStatistics
} from "@/components/Statistics/StatisticsHelper";
import CheckerStatisticsTable from "./CheckerStatisticsTable";

export default {
  name: "CheckerStatistics",
  components: {
    CheckerStatisticsTable
  },
  mixins: [ BaseStatistics, ReviewStatusMixin, SeverityMixin, ToCSV ],

  data() {
    return {
      loading: false,
      statistics: []
    };
  },

  methods: {
    downloadCSV() {
      const data = [
        [
          "Checker", "Severity", "Unreviewed",
          "Confirmed bug", "Outstanding reports (Unreviewed + Confirmed)",
          "False positive", "Intentional",
          "Suppressed reports (False positive + Intentional)", "All reports"
        ],
        ...this.statistics.map(stat => {
          return [
            stat.checker, this.severityFromCodeToString(stat.severity),
            stat.unreviewed.count, stat.confirmed.count,
            stat.outstanding.count, stat.falsePositive.count,
            stat.intentional.count, stat.suppressed.count, stat.reports.count,
          ];
        })
      ];

      this.toCSV(data, "codechecker_checker_statistics.csv");
    },

    getStatistics: getCheckerStatistics,

    async fetchStatistics() {
      this.loading = true;

      const { runIds, reportFilter, cmpData } = this.getStatisticsFilters();
      this.statistics =
        await getCheckerStatistics(runIds, reportFilter, cmpData);

      await this.fetchDifference("checker");

      this.loading = false;
    }
  }
};
</script>
