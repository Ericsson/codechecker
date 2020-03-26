<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h3 class="title primary--text">
          Checker statistics
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
          :disable-pagination="true"
          :hide-default-footer="true"
          :must-sort="true"
          :loading="loading"
          item-key="checker"
        >
          <template v-slot:header.unreviewed="{ header }">
            <review-status-icon
              :status="ReviewStatus.UNREVIEWED"
              :size="16"
              left
            />
            {{ header.text }}
          </template>

          <template v-slot:header.confirmed="{ header }">
            <review-status-icon
              :status="ReviewStatus.CONFIRMED"
              :size="16"
              left
            />
            {{ header.text }}
          </template>

          <template v-slot:header.falsePositive="{ header }">
            <review-status-icon
              :status="ReviewStatus.FALSE_POSITIVE"
              :size="16"
              left
            />
            {{ header.text }}
          </template>

          <template v-slot:header.intentional="{ header }">
            <review-status-icon
              :status="ReviewStatus.INTENTIONAL"
              :size="16"
              left
            />
            {{ header.text }}
          </template>

          <template v-slot:header.reports="{ header }">
            <detection-status-icon
              :status="DetectionStatus.UNRESOLVED"
              :size="16"
              left
            />
            {{ header.text }}
          </template>

          <template #item.checker="{ item }">
            <router-link
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'checker-name': item.checker
              }}"
            >
              {{ item.checker }}
            </router-link>
          </template>

          <template #item.severity="{ item }">
            <router-link
              class="severity"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'checker-name': item.checker,
                'severity': severityFromCodeToString(
                  item.severity)
              }}"
            >
              <severity-icon :status="item.severity" />
            </router-link>
          </template>

          <template #item.unreviewed="{ item }">
            <router-link
              v-if="item.unreviewed"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'checker-name': item.checker,
                'review-status': reviewStatusFromCodeToString(
                  ReviewStatus.UNREVIEWED)
              }}"
            >
              {{ item.unreviewed }}
            </router-link>
          </template>

          <template #item.confirmed="{ item }">
            <router-link
              v-if="item.confirmed"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'checker-name': item.checker,
                'review-status': reviewStatusFromCodeToString(
                  ReviewStatus.CONFIRMED)
              }}"
            >
              {{ item.confirmed }}
            </router-link>
          </template>

          <template #item.falsePositive="{ item }">
            <router-link
              v-if="item.falsePositive"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'checker-name': item.checker,
                'review-status': reviewStatusFromCodeToString(
                  ReviewStatus.FALSE_POSITIVE)
              }}"
            >
              {{ item.falsePositive }}
            </router-link>
          </template>

          <template #item.intentional="{ item }">
            <router-link
              v-if="item.intentional"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'checker-name': item.checker,
                'review-status': reviewStatusFromCodeToString(
                  ReviewStatus.INTENTIONAL)
              }}"
            >
              {{ item.intentional }}
            </router-link>
          </template>

          <template #item.reports="{ item }">
            <router-link
              v-if="item.reports"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'checker-name': item.checker
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

import {
  DetectionStatus,
  ReportFilter,
  ReviewStatus
} from "@cc/report-server-types";

import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";

import { ReviewStatusMixin, SeverityMixin, ToCSV } from "@/mixins";

export default {
  name: "CheckerStatistics",
  components: {
    DetectionStatusIcon,
    ReviewStatusIcon,
    SeverityIcon
  },
  mixins: [ ReviewStatusMixin, SeverityMixin,ToCSV ],

  props: {
    namespace: { type: String, required: true }
  },

  data() {
    return {
      ReviewStatus,
      DetectionStatus,
      loading: false,
      headers: [
        {
          text: "Checker",
          value: "checker"
        },
        {
          text: "Severity",
          value: "severity",
          align: "center"
        },
        {
          text: "Unreviewed",
          value: "unreviewed",
          align: "center"
        },
        {
          text: "Confirmed bug",
          value: "confirmed",
          align: "center"
        },
        {
          text: "False positive",
          value: "falsePositive",
          align: "center"
        },
        {
          text: "Intentional",
          value: "intentional",
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
        [
          "Checker", "Severity", "All reports", "Resolved", "Unreviewed",
          "Confirmed bug", "False positive", "Intentional"
        ],
        ...this.statistics.map(stat => {
          return [
            stat.checker, this.severityFromCodeToString(stat.severity),
            stat.reports, stat.resolved, stat.unreviewed, stat.confirmed,
            stat.falsePositive, stat.intentional
          ];
        })
      ];

      this.toCSV(data, "codechecker_checker_statistics.csv");
    },

    fetchStatistics() {
      this.loading = true;
      const runIds = this.runIds;
      const cmpData = null;

      const limit = null;
      const offset = null;

      const queries = [
        { field: null, values: null },
        { field: "reviewStatus", values: [ ReviewStatus.UNREVIEWED ] },
        { field: "reviewStatus", values: [ ReviewStatus.CONFIRMED ] },
        { field: "reviewStatus", values: [ ReviewStatus.FALSE_POSITIVE ] },
        { field: "reviewStatus", values: [ ReviewStatus.INTENTIONAL ] },
        { field: "detectionStatus", values: [ DetectionStatus.RESOLVED ] }
      ].map(q => {
        const reportFilter = new ReportFilter(this.reportFilter);

        if (q.field) {
          reportFilter[q.field] = q.values;
        }

        return new Promise(resolve => {
          ccService.getClient().getCheckerCounts(runIds, reportFilter, cmpData,
            limit, offset, handleThriftError(checkerCounts => {
              const obj = {};
              checkerCounts.forEach(item => { obj[item.name] = item; });
              resolve(obj);
            }));
        });

      });
      Promise.all(queries).then(res => {
        const checkers = res[0];
        const checkerNames = Object.keys(checkers);

        this.statistics = checkerNames.map(key => {
          return {
            checker       : key,
            severity      : checkers[key].severity,
            reports       : checkers[key].count.toNumber(),
            unreviewed    : this.resultToNumber(res[1][key]),
            confirmed     : this.resultToNumber(res[2][key]),
            falsePositive : this.resultToNumber(res[3][key]),
            intentional   : this.resultToNumber(res[4][key]),
            resolved      : this.resultToNumber(res[5][key]),
          };
        });
        this.loading = false;
      });
    },

    resultToNumber(value) {
      return value !== undefined ? value.count.toNumber() : 0;
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .severity {
  text-decoration: none;
}
</style>
