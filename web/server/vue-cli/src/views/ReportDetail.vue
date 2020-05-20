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
              small
              class="mb-2"
              color="primary"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'report-id': undefined
              }}"
            >
              <v-icon
                left
                small
              >
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
        @toggle:comments="showComments = !showComments"
        @update:report="loadReport"
      />
    </pane>
  </splitpanes>
</template>

<script>
import { Pane, Splitpanes } from "splitpanes";
import { mapState } from "vuex";

import { ccService, handleThriftError } from "@cc-api";
import {
  MAX_QUERY_SIZE,
  Order,
  ReportFilter,
  SortMode,
  SortType
} from "@cc/report-server-types";

import { FillHeight } from "@/directives";
import { Report } from "@/components/Report";
import { ReportTree } from "@/components/Report/ReportTree";

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
      treeItem: null,
      showComments: true
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
    const reportId = this.$router.currentRoute.query["report-id"];
    const reportHash = this.$router.currentRoute.query["report-hash"];
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
      ccService.getClient().getReport(reportId,
        handleThriftError(reportData => {
          this.report = reportData;
        }));
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
        isUnique: false,
        reportHash: [ reportHash ]
      });

      ccService.getClient().getRunResults(this.runIds, limit, offset,
        [ sortType ], reportFilter, this.cmpData, getDetails,
        handleThriftError(reports => {
          this.report = reports[0];
        }));
    },

    updateUrl() {
      const reportId = this.report.reportId.toString();
      const currentReportId = this.$router.currentRoute.query["report-id"];
      if (reportId !== currentReportId) {
        this.$router.replace({
          query: {
            ...this.$route.query,
            "report-id": reportId
          }
        }).catch(() => {});
      }
    },

    onReportTreeClick(item) {
      if (!item) return;

      if (item.report) {
        this.report = item.report;
        this.updateUrl();
      }

      this.treeItem = item;
    }
  }
};
</script>

<style lang="scss" scoped>
.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}
</style>
