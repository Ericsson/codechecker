<template>
  <div id="severity-statistics">
    <h3>Severity statistics</h3>
    <v-data-table
      :headers="headers"
      :items="statistics"
      :hide-default-footer="true"
      item-key="severity"
    />
  </div>
</template>

<script>
import VDataTable from "Vuetify/VDataTable/VDataTable";

import { ccService } from '@cc-api';

export default {
  name: 'SeverityStatistics',
  components: {
    VDataTable
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
            severity: severity,
            reports: statistics[severity]
          };
        })
      });
    }
  }
}
</script>
