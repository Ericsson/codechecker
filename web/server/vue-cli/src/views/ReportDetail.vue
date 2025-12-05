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
          density="compact"
          variant="outlined"
        >
          The report (
          report ID: <i>{{ route.query["report-id"] }}</i>,
          report hash: <i>{{ route.query["report-hash"] }}</i>,
          file path:
          <i>"{{ route.query["report-filepath"] }}"</i>
          ) was removed from the database.

          <span v-if="!route.query['report-hash']">
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
    <pane
      size="20"
    >
      <v-container
        fluid
        class="pa-0"
      >
        <v-row
          no-gutters
        >
          <v-col
            class="px-2"
          >
            <v-btn
              id="back-to-reports-btn"
              block
              variant="outlined"
              rounded="xs"
              size="small"
              class="mb-2"
              color="primary"
              :to="{ name: 'reports', query: {
                ...route.query,
                'report-id': undefined,
                'report-filepath': undefined,
                ...reportFilter.reportHash ? {} : {
                  'report-hash' : undefined 
                }
              }}"
            >
              <v-icon
                size="small"
              >
                mdi-arrow-left
              </v-icon>
              Back to reports
            </v-btn>
          </v-col>
        </v-row>
        <v-row
          no-gutters
        >
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
      <Report
        :tree-item="treeItem"
        @toggle:comments="showComments = !showComments"
        @update:report="loadReport"
        @update-review-data="updateReviewData"
      />
    </pane>
  </splitpanes>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";
import { Pane, Splitpanes } from "splitpanes";

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

const vFillHeight = FillHeight;

const route = useRoute();
const router = useRouter();
const store = useStore();

const report = ref(null);
const treeItem = ref(null);
const showComments = ref(true);
const reportNotFound = ref(false);
const reviewStatus = ref(null);

const runIds = computed(function() {
  return store.state.report.runIds;
});

const reportFilter = computed(function() {
  return store.state.report.reportFilter;
});

const cmpData = computed(function() {
  return store.state.report.cmpData;
});

onMounted(function() {
  const _reportId = route.query["report-id"];
  const _reportHash = route.query["report-hash"];
  loadReport(_reportId, _reportHash);
});

function loadReport(reportId, reportHash) {
  if (reportId) {
    loadReportById(reportId).catch(() => {
      if (reportHash) {
        loadReportByHash(reportHash);
      } else {
        reportNotFound.value = true;
      }
    });
  } else if (reportHash) {
    loadReportByHash(reportHash);
  }
}

function loadReportById(reportId) {
  return new Promise((_res, _rej) => {
    ccService.getClient().getReport(
      reportId,
      handleThriftError(_reportData => {
        report.value = _reportData;
        treeItem.value = { report: _reportData };
        _res(true);
      }, _err => {
        console.warn("Failed to get report for ID:", reportId);
        console.warn(_err);
        _rej(_err);
      }));
  });
}

function loadReportByHash(reportHash) {
  const _limit = MAX_QUERY_SIZE;
  const _offset = 0;
  const _getDetails = false;

  const _sortType = new SortMode({
    type: SortType.BUG_PATH_LENGTH,
    ord: Order.ASC
  });

  const _filePath = route.query["report-filepath"];
  const _reportFilter = new ReportFilter({
    ...reportFilter.value,
    isUnique: false,
    reportHash: [ reportHash ],
    filePath: [ _filePath ]
  });

  ccService.getClient().getRunResults(
    runIds.value,
    _limit,
    _offset,
    [ _sortType ],
    _reportFilter,
    cmpData.value,
    _getDetails,
    handleThriftError(_reports => {
      if (_reports.length) {
        report.value = _reports[0];
      } else {
        reportNotFound.value = true;
      }
    }));
}

function updateUrl() {
  const _reportId = report.value.reportId.toString();
  const _currentReportId = route.query["report-id"];
  if (_reportId !== _currentReportId) {
    router.replace({
      query: {
        ...route.query,
        "report-id": _reportId
      }
    }).catch(() => {});
  }
}

function onReportTreeClick(item) {
  if (!item) return;

  if (item.report) {
    report.value = item.report;
    updateUrl();
  }

  treeItem.value = item;
}

function updateReviewData(newReviewData, reportId) {
  reviewStatus.value = newReviewData.status;
  loadReport(reportId);
}
</script>

<style lang="scss" scoped>
.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}
</style>
