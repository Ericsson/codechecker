<template>
  <v-container :fluid="true">
    <v-row>
      <v-col>
        <report-tree
          :report="report"
        />
      </v-col>
      <v-col cols="9">
        <report
          :report="report"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import VContainer from "Vuetify/VGrid/VContainer";
import VRow from "Vuetify/VGrid/VRow";
import VCol from "Vuetify/VGrid/VCol";

import { ccService } from '@cc-api';

import Report from '@/components/Report';
import ReportTree from '@/components/ReportTree/ReportTree';

export default {
  name: 'ReportDetail',
  components: {
    VContainer, VRow, VCol,
    Report,
    ReportTree
  },
  data() {
    return {
      report: null
    };
  },
  mounted() {
    const reportId = this.$router.currentRoute.query["reportId"] || 1;
    this.loadReport(reportId);
  },
  methods: {
    loadReport(reportId) {
      ccService.getClient().getReport(reportId, (err, reportData) => {
        this.report = reportData;
      });
    }
  }
}
</script>
