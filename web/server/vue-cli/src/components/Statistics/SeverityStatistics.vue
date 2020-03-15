<template>
  <v-container fluid>
    <v-row>
      <v-col cols="auto">
        <h3 class="title primary--text">
          Severity statistics
          <v-btn
            color="primary"
            outlined
            @click="downloadCSV"
          >
            Export CSV
          </v-btn>
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
import { SeverityMixin, ToCSV } from "@/mixins";

export default {
  name: "SeverityStatistics",
  components: {
    DetectionStatusIcon,
    SeverityIcon
  },
  mixins: [ SeverityMixin, ToCSV ],

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

  mounted() {
    // The fetchStatistics function which initalizes this component is called
    // dynamically by the parent component. If Hot Module Replacement is
    // enabled and this component will be replaced then this initialization
    // will not be made. For this reason on component replacement we will save
    // the data and we will initalize the new component with this data.
    if (process.env.NODE_ENV !== "production") {
      if (module.hot) {
        if (module.hot.data) {
          this.statistics = module.hot.data.statistics;
        }

        module.hot.dispose(data => data["statistics"] = this.statistics);
      }
    }
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

<style lang="scss" scoped>
::v-deep .severity {
  text-decoration: none;
}
</style>
