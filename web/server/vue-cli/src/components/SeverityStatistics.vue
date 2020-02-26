<template>
  <v-container fluid>
    <v-row>
      <v-col cols="auto">
        <h3 class="title primary--text">
          Severity statistics
        </h3>
        <v-data-table
          :headers="headers"
          :items="statistics"
          :hide-default-footer="true"
          item-key="severity"
        >
          <template #item.severity="{ item }">
            <severity-icon :status="item.severity" />
          </template>
        </v-data-table>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapState } from "vuex";
import { ccService } from "@cc-api";

import { SeverityIcon } from "@/components/Icons";

export default {
  name: "SeverityStatistics",
  components: {
    SeverityIcon
  },

  props: {
    namespace: { type: String, required: true }
  },

  data() {
    return {
      headers: [
        {
          text: "Severity",
          value: "severity"
        },
        {
          text: "All reports",
          value: "reports"
        }
      ],
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
    fetchStatistics() {
      const runIds = this.runIds;
      const reportFilter = this.reportFilter;
      const cmpData = null;

      ccService.getClient().getSeverityCounts(runIds, reportFilter, cmpData,
        (err, statistics) => {
          this.statistics = Object.keys(statistics).map(severity => {
            return {
              severity: parseInt(severity),
              reports: statistics[severity]
            };
          });
        });
    }
  }
};
</script>
