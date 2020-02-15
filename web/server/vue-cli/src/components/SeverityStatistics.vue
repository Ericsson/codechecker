<template>
  <div id="severity-statistics">
    <h3>Severity statistics</h3>
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
  </div>
</template>

<script>
import { ccService } from "@cc-api";

import { SeverityIcon } from "@/components/Icons";

export default {
  name: "SeverityStatistics",
  components: {
    SeverityIcon
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


  created() {
    this.fetchStatistics();
  },

  methods: {
    fetchStatistics() {
      const runIds = null;
      const reportFilter = null;
      const cmpData = null;

      ccService.getClient().getSeverityCounts(runIds, reportFilter, cmpData,
      (err, statistics) => {
        this.statistics = Object.keys(statistics).map((severity) => {
          return {
            severity: parseInt(severity),
            reports: statistics[severity]
          };
        })
      });
    }
  }
}
</script>
