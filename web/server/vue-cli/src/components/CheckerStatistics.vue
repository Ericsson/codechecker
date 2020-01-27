<template>
  <div id="checker-statistics">
    <h3>Checker statistics</h3>
    <v-data-table
      :headers="headers"
      :items="statistics"
      :hide-default-footer="true"
      item-key="checker"
    >
      <template #item.severity="{ item }">
        <severity-icon :status="item.severity" />
      </template>
    </v-data-table>
  </div>
</template>

<script>
import VDataTable from "Vuetify/VDataTable/VDataTable";

import { ccService } from "@cc-api";
import {
  DetectionStatus,
  ReportFilter,
  ReviewStatus
} from "@cc/report-server-types";

import { SeverityIcon } from "@/components/icons";

export default {
  name: "CheckerStatistics",
  components: {
    VDataTable,
    SeverityIcon
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


  created() {
    this.fetchStatistics();
  },

  methods: {
    fetchStatistics() {
      // TODO: this should be controlled by the filter bar.
      const runIds = null;
      const cmpData = null;

      const limit = null;
      const offset = null;

      // TODO: this should be controlled by the filter bar.
      const isUnique = true;

      const queries = [
        { field: null, values: null },
        { field: "reviewStatus", values: [ ReviewStatus.UNREVIEWED ] },
        { field: "reviewStatus", values: [ ReviewStatus.CONFIRMED ] },
        { field: "reviewStatus", values: [ ReviewStatus.FALSE_POSITIVE ] },
        { field: "reviewStatus", values: [ ReviewStatus.INTENTIONAL ] },
        { field: "detectionStatus", values: [ DetectionStatus.RESOLVED ] }
      ].map((q) => {
        const reportFilter = new ReportFilter();
        reportFilter.isUnique = isUnique;

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
