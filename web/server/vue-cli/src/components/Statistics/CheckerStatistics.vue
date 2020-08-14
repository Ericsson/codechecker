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
import { mapState } from "vuex";

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

  computed: {
    ...mapState({
      runIds(state, getters) {
        return getters[`${this.namespace}/getRunIds`];
      },
      reportFilter(state, getters) {
        return getters[`${this.namespace}/getReportFilter`];
      }
    })
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

    async fetchStatistics() {
      this.loading = true;
      const runIds = this.runIds;
      const reportFilter = this.reportFilter;

      this.statistics = await getCheckerStatistics(runIds, reportFilter);

      this.loading = false;
    }
  }
};
</script>
