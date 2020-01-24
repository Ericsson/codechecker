<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <v-container fluid>
        <v-row no-gutters>
          <v-col>
            <v-btn
              block
              outlined
              tile
              class="mb-2"
              color="primary"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                reportId: undefined
              }}"
            >
              <v-icon left>
                mdi-arrow-left
              </v-icon>
              Back to reports
            </v-btn>
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col>
            <report-tree
              :report="report"
              @click="onReportTreeClick"
            />
          </v-col>
        </v-row>
      </v-container>
    </pane>
    <pane>
      <report
        :tree-item="treeItem"
      />
    </pane>
  </splitpanes>
</template>

<script>
import { Splitpanes, Pane } from 'splitpanes';
import VContainer from "Vuetify/VGrid/VContainer";
import VRow from "Vuetify/VGrid/VRow";
import VCol from "Vuetify/VGrid/VCol";
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";

import { ccService } from '@cc-api';

import Report from '@/components/Report';
import ReportTree from '@/components/ReportTree/ReportTree';

export default {
  name: 'ReportDetail',
  components: {
    Splitpanes, Pane,
    VContainer, VRow, VCol, VBtn, VIcon,
    Report,
    ReportTree
  },
  data() {
    return {
      report: null,
      treeItem: null
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
    },

    onReportTreeClick(item) {
      if (!item) return;

      this.treeItem = item;
    }
  }
}
</script>
