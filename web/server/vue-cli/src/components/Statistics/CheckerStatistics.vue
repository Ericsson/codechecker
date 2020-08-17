<template>
  <v-container fluid>
    <v-row>
      <v-col>
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
import BaseStatistics from "./BaseStatistics";
import CheckerStatisticsTable from "./CheckerStatisticsTable";
import { getCheckerStatistics } from "./StatisticsHelper";

export default {
  name: "CheckerStatistics",
  components: {
    CheckerStatisticsTable
  },
  mixins: [ BaseStatistics, ReviewStatusMixin, SeverityMixin, ToCSV ],

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
        [
          "Checker", "Severity", "All reports", "Unreviewed",
          "Confirmed bug", "False positive", "Intentional"
        ],
        ...this.statistics.map(stat => {
          return [
            stat.checker, this.severityFromCodeToString(stat.severity),
            stat.reports, stat.unreviewed, stat.confirmed,
            stat.falsePositive, stat.intentional
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

      await this.fetchDifference("component");

      this.loading = false;
    }
  }
};
</script>
