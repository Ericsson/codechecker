<template>
  <div>
    <v-data-table
      :headers="headers"
      :items="reports"
      item-key="name"
    />
  </div>
</template>

<script>
import VDataTable from "Vuetify/VDataTable/VDataTable";

import { ccService } from '@cc-api';

export default {
  name: 'Reports',
  components: {
    VDataTable
  },

  data() {
    return {
      headers: [
        {
          text: "Report hash",
          value: "bugHash"
        },
        {
          text: "File",
          value: "checkedFile"
        },
        {
          text: "Message",
          value: "checkerMsg"
        },
        {
          text: "Checker name",
          value: "checkerId"
        },
        {
          text: "Severity",
          value: "severity"
        },
        {
          text: "Bug path length",
          value: "bugPathLength"
        },
        {
          text: "Review status",
          value: "reviewData"
        },
        {
          text: "Detection status",
          value: "detectionStatus"
        }
      ],
      reports: []
    };
  },

  created() {
    this.fetchReports();
  },

  methods: {
    fetchReports() {
      const runIds = null;
      const limit = null;
      const offset = null;
      const sortType = null;
      const reportFilter = null;
      const cmpData = null;
      const getDetails = false;

      ccService.getClient().getRunResults(runIds, limit, offset, sortType,
      reportFilter, cmpData, getDetails, (err, reports) => {
        this.reports = reports;
      });
    }
  }
}
</script>
