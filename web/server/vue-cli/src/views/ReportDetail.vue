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
        class="pa-0"
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
              :review-status="reviewStatus"
              @click="onReportTreeClick"
            />
          </v-col>
        </v-row>
      </v-container>
    </pane>

    <pane>
      <report
        :tree-item="treeItem"
        :coverage-data="treeItem?.coverageData"
        @toggle:comments="showComments = !showComments"
        @update:report="loadReport"
        @update-review-data="updateReviewData"
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
      reportNotFound: false,
      reviewStatus: null,
      coverageData: null
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

    async onReportTreeClick(item) {
      if (!item) return;

      if (item.report) {
        this.report = item.report;
        this.updateUrl();
      }

      if (item.report && item.report.fileId) {
        try {
          // Original backend fetching method (commented out)
          // const coverageData = await ccService.getCodeCoverage(
          //   item.report.fileId,
          //   this.runIds
          // );
          // item.coverageData = coverageData;

          // Mock data for testing
          const mockCoverageData = {
            fileId: item.report.fileId,
            filePath: item.report.checkedFile,
            totalLines: 14,
            coveredLines: 8,
            uncoveredLines: 6,
            coveragePercentage: 57.1,
            lineCoverage: [
              {
                lineNumber: 1,
                covered: true,
                partiallyCovered: false,
                executionCount: 5
              },
              {
                lineNumber: 2,
                covered: false,
                partiallyCovered: false
              },
              {
                lineNumber: 3,
                covered: true,
                partiallyCovered: false,
                executionCount: 10
              },
              {
                lineNumber: 4,
                covered: true,
                partiallyCovered: true,
                executionCount: 3
              },
              {
                lineNumber: 5,
                covered: false,
                partiallyCovered: false
              },
              {
                lineNumber: 6,
                covered: true,
                partiallyCovered: false,
                executionCount: 2
              },
              {
                lineNumber: 7,
                covered: true,
                partiallyCovered: true,
                executionCount: 8
              },
              {
                lineNumber: 8,
                covered: false,
                partiallyCovered: false
              },
              {
                lineNumber: 9,
                covered: true,
                partiallyCovered: false,
                executionCount: 4
              },
              {
                lineNumber: 10,
                covered: true,
                partiallyCovered: true,
                executionCount: 6
              },
              {
                lineNumber: 11,
                covered: false,
                partiallyCovered: false
              },
              {
                lineNumber: 12,
                covered: true,
                partiallyCovered: false,
                executionCount: 7
              },
              {
                lineNumber: 13,
                covered: true,
                partiallyCovered: false,
                executionCount: 9
              },
              {
                lineNumber: 14,
                covered: false,
                partiallyCovered: false
              }
            ]
          };
          
          console.log("Using mock coverage data:", mockCoverageData);
          item.coverageData = mockCoverageData;
        } catch (err) {
          console.error("Failed to load coverage data:", err);
        }
      }

      this.treeItem = item;
    },

    updateReviewData(newReviewData, reportId) {
      this.reviewStatus = newReviewData.status;
      this.loadReport(reportId);
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
