<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h3 class="title primary--text">
          Checker statistics
        </h3>
        <v-data-table
          :headers="headers"
          :items="statistics"
          :hide-default-footer="true"
          item-key="checker"
        >
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
            <severity-icon :status="item.severity" />
          </template>

          <!-- TODO Get review status filter id from the component and use
              the encode function to encode the value -->
          <template #item.unreviewed="{ item }">
            <router-link
              v-if="item.unreviewed"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'checker-name': item.checker,
                'review-status': 'Unreviewed'
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
                'review-status': 'Confirmed'
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
                'review-status': 'False_positive'
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
                'review-status': 'Intentional'
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

import { ccService } from "@cc-api";
import {
  DetectionStatus,
  ReportFilter,
  ReviewStatus
} from "@cc/report-server-types";

import { SeverityIcon } from "@/components/Icons";

export default {
  name: "CheckerStatistics",
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
          text: "Checker",
          value: "checker"
        },
        {
          text: "Severity",
          value: "severity"
        },
        {
          text: "Unreviewed",
          value: "unreviewed"
        },
        {
          text: "Confirmed bug",
          value: "confirmed"
        },
        {
          text: "False positive",
          value: "falsePositive"
        },
        {
          text: "Intentional",
          value: "intentional"
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

  created() {
    this.fetchStatistics();
  },

  methods: {
    fetchStatistics() {
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
      ].map((q) => {
        const reportFilter = new ReportFilter(this.reportFilter);

        if (q.field) {
          reportFilter[q.field] = q.values;
        }

        return new Promise((resolve) => {
          ccService.getClient().getCheckerCounts(runIds, reportFilter, cmpData,
          limit, offset, (err, checkerCounts) => {
            const obj = {};
            checkerCounts.forEach((item) => { obj[item.name] = item; });
            resolve(obj);
          });
        });

      });
      Promise.all(queries).then(res => {
        const checkers = res[0];
        const checkerNames = Object.keys(checkers);

        this.statistics = checkerNames.map((key) => {
          return {
            checker       : key,
            severity      : checkers[key].severity,
            reports       : checkers[key].count,
            unreviewed    : res[1][key] !== undefined ? res[1][key].count : 0,
            confirmed     : res[2][key] !== undefined ? res[2][key].count : 0,
            falsePositive : res[3][key] !== undefined ? res[3][key].count : 0,
            intentional   : res[4][key] !== undefined ? res[4][key].count : 0,
            resolved      : res[5][key] !== undefined ? res[5][key].count : 0
          };
        });
      });
    }
  }
}
</script>
