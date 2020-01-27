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
import { mapState } from "vuex";

import { ccService } from "@cc-api";
import {
  MAX_QUERY_SIZE,
  Order,
  ReportFilter,
  SortMode,
  SortType
} from "@cc/report-server-types";

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
  computed: {
    ...mapState({
      runIds: state => state.report.runIds,
      reportFilter: state => state.report.reportFilter,
      cmpData: state => state.report.cmpData,
    })
  },

  mounted() {
    const reportId = this.$router.currentRoute.query["reportId"];
    const reportHash = this.$router.currentRoute.query["reportHash"];
    this.loadReport(reportId, reportHash);
  },

  methods: {
    loadReport(reportId, reportHash) {
      if (reportId) {
        this.loadReportById(reportId);
      } else if (reportHash) {
        this.loadReportByHash(reportHash);
      }
    },

    loadReportById(reportId) {
      ccService.getClient().getReport(reportId, (err, reportData) => {
        this.report = reportData;
      });
    },

    loadReportByHash(reportHash) {
      const limit = MAX_QUERY_SIZE;
      const offset = 0;
      const getDetails = false;

      const sortType = new SortMode({
        type: SortType.BUG_PATH_LENGTH,
        ord: Order.ASC
      });

      const reportFilter = new ReportFilter({
        ...this.reportFilter,
        reportHash: [ reportHash ]
      });

      ccService.getClient().getRunResults(this.runIds, limit, offset,
      [ sortType ], reportFilter, this.cmpData, getDetails,
      (err, reports) => {
        this.report = reports[0];
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
