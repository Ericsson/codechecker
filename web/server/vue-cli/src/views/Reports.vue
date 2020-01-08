<template>
  <div>
    <v-data-table
      :headers="headers"
      :items="reports"
      item-key="name"
    >
      <template #item.bugPathLength="{ item }">
        <v-chip :color="getBugPathLenColor(item.bugPathLength)">
          {{ item.bugPathLength }}
        </v-chip>
      </template>
    </v-data-table>
  </div>
</template>

<script>
import VDataTable from "Vuetify/VDataTable/VDataTable";
import VChip from "Vuetify/VChip/VChip";

import { ccService } from '@cc-api';

import { BugPathLengthColorMixin } from '@/mixins';

export default {
  name: 'Reports',
  components: {
    VDataTable, VChip
  },
  mixins: [ BugPathLengthColorMixin ],

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
          value: "bugPathLength",
          align: 'center'
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
