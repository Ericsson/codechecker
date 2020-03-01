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
import { ccService } from "@cc-api";

import { SeverityIcon } from "@/components/Icons";
import { SeverityMixin } from "@/mixins";

export default {
  name: "SeverityStatistics",
  components: {
    SeverityIcon
  },
  mixins: [ SeverityMixin ],

  props: {
    namespace: { type: String, required: true }
  },

  data() {
    return {
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

<style lang="sass" scoped>
::v-deep .severity {
  text-decoration: none;
}
</style>
