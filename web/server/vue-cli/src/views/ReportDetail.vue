<template>
  <v-container
    v-if="reportNotFound"
    class="text-center"
    fill-height
  >
    <v-row align="center" justify="center">
      <v-col class="error--text" cols="6">
        <h1 class="display-2">
          404 - Report not found!
        </h1>

        <v-alert
          class="mt-4"
          type="error"
          dense
          outlined
          text
        >
          The report (
          report ID: <i>{{ $router.currentRoute.query["report-id"] }}</i>,
          report hash: <i>{{ $router.currentRoute.query["report-hash"] }}</i>,
          file path:
          <i>"{{ $router.currentRoute.query["report-filepath"] }}"</i>
          ) was removed from the database.

          <span v-if="!$router.currentRoute.query['report-hash']">
            Unfortunately, your hyperlink was copied from an older version of
            CodeChecker and the request does not contain the <i>report-hash</i>
            parameter which could be used as a fallback mechanism.
          </span>
        </v-alert>
      </v-col>
    </v-row>
  </v-container>

  <splitpanes
    v-else
    class="default-theme"
  >
    <pane size="20">
      <v-container
        fluid
        class="px-0"
      >
        <v-row no-gutters>
          <v-col class="px-2">
            <v-btn
              id="back-to-reports-btn"
              block
              outlined
              tile
              small
              class="mb-2"
              color="primary"
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'report-id': undefined,
                'report-filepath': undefined,
                ...(
                  reportFilter.reportHash ? {} : { 'report-hash' : undefined }
                )
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
      showComments: true,
      reportNotFound: false
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
        this.loadReportById(reportId).catch(() => {
          if (reportHash) {
            this.loadReportByHash(reportHash);
          } else {
            this.reportNotFound = true;
          }
        });
      } else if (reportHash) {
        this.loadReportByHash(reportHash);
      }
    },

    loadReportById(reportId) {
      return new Promise((res, rej) => {
        ccService.getClient().getReport(reportId,
          handleThriftError(reportData => {
            this.report = reportData;
            res(true);
          }, err => {
            console.warn("Failed to get report for ID:", reportId);
            console.warn(err);
            rej(err);
          }));
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

      const filePath = this.$router.currentRoute.query["report-filepath"];
      const reportFilter = new ReportFilter({
        ...this.reportFilter,
        isUnique: false,
        reportHash: [ reportHash ],
        filePath: [ filePath ]
      });

      ccService.getClient().getRunResults(this.runIds, limit, offset,
        [ sortType ], reportFilter, this.cmpData, getDetails,
        handleThriftError(reports => {
          if (reports.length) {
            this.report = reports[0];
          } else {
            this.reportNotFound = true;
          }
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
