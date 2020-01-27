<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <v-container
        fluid
        class="px-0"
      >
        <v-row no-gutters>
          <v-col class="px-2">
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
              v-fill-height
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
import { Splitpanes, Pane } from "splitpanes";

import { ccService } from "@cc-api";

import { FillHeight } from "@/directives";
import Report from "@/components/Report";
import ReportTree from "@/components/ReportTree/ReportTree";

export default {
  name: "ReportDetail",
  components: {
    Splitpanes,
    Pane,
    Report,
    ReportTree
  },
  directives: { FillHeight },
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

<style lang="scss" scoped>
.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}
</style>
