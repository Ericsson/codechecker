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
          :must-sort="true"
          item-key="severity"
        >
          <template v-slot:header.reports="{ header }">
            <detection-status-icon
              :status="DetectionStatus.UNRESOLVED"
              :size="16"
              left
            />
            {{ header.text }}
          </template>

          <template #item.severity="{ item }">
            <router-link
              class="severity"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'severity': severityFromCodeToString(
                  item.severity)
              }}"
            >
              <severity-icon :status="item.severity" />
            </router-link>
          </template>

          <template #item.reports="{ item }">
            <router-link
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'severity': severityFromCodeToString(
                  item.severity)
              }}"
            >
              {{ item.reports }}
            </router-link>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapState } from "vuex";
import { ccService, handleThriftError } from "@cc-api";
import { DetectionStatus } from "@cc/report-server-types";

import { DetectionStatusIcon, SeverityIcon } from "@/components/Icons";
import { SeverityMixin } from "@/mixins";

export default {
  name: "SeverityStatistics",
  components: {
    DetectionStatusIcon,
    SeverityIcon
  },
  mixins: [ SeverityMixin ],

  props: {
    namespace: { type: String, required: true }
  },

  data() {
    return {
      DetectionStatus,
      headers: [
        {
          text: "Severity",
          value: "severity",
          align: "center"
        },
        {
          text: "All reports",
          value: "reports",
          align: "center"
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
        handleThriftError(statistics => {
          this.statistics = Object.keys(statistics).map(severity => {
            return {
              severity: parseInt(severity),
              reports: statistics[severity]
            };
          });
        }));
    }
  }
};
</script>

<style lang="sass" scoped>
::v-deep .severity {
  text-decoration: none;
}
</style>
