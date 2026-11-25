<template>
  <v-container
    v-if="reportNotFound"
    class="d-flex align-center justify-center fill-height"
    fluid
  >
    <v-card
      id="report-not-found"
      class="pa-6 text-center"
      max-width="640"
      width="100%"
      variant="flat"
      rounded="lg"
    >
      <v-icon
        color="error"
        size="72"
        class="mb-2"
      >
        mdi-file-search-outline
      </v-icon>

      <v-card-title class="text-h5 text-wrap">
        Report not found
      </v-card-title>

      <v-card-text>
        <p class="mb-4">
          We could not find the report you are looking for. It may have been
          deleted, or the URL may be incorrect.
        </p>

        <v-list
          v-if="requestedDetails.length"
          density="compact"
          lines="one"
          class="text-left bg-transparent mb-4"
        >
          <v-list-item
            v-for="detail in requestedDetails"
            :key="detail.label"
          >
            <template v-slot:prepend>
              <v-icon size="small">
                {{ detail.icon }}
              </v-icon>
            </template>
            <v-list-item-title class="text-body-2">
              <span class="font-weight-medium">{{ detail.label }}:</span>
              <code class="ml-1">{{ detail.value }}</code>
            </v-list-item-title>
          </v-list-item>
        </v-list>

        <v-alert
          v-if="!route.query[ 'report-hash' ]"
          type="info"
          density="compact"
          variant="tonal"
          class="text-left"
        >
          This link was probably copied from an older version of CodeChecker
          and does not contain the <i>report-hash</i> parameter, which could
          be used as a fallback to find the report.
        </v-alert>
      </v-card-text>

      <v-card-actions class="justify-center">
        <v-btn
          id="back-to-reports-btn"
          color="primary"
          class="px-4"
          variant="flat"
          prepend-icon="mdi-arrow-left"
          :to="backToReportsRoute"
        >
          Back to reports
        </v-btn>
      </v-card-actions>
    </v-card>
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

const requestedDetails = computed(function() {
  return [
    { label: "Report ID", icon: "mdi-identifier", key: "report-id" },
    { label: "Report hash", icon: "mdi-pound", key: "report-hash" },
    { label: "File path", icon: "mdi-file-outline", key: "report-filepath" }
  ]
    .filter(d => route.query[ d.key ])
    .map(d => ({ ...d, value: route.query[ d.key ] }));
});

const backToReportsRoute = computed(function() {
  return {
    name: "reports",
    query: {
      ...route.query,
      "report-id": undefined,
      "report-hash": undefined,
      "report-filepath": undefined
    }
  };
});

const runIds = computed(function() {
  return store.state.runIds;
});

const reportFilter = computed(function() {
  return store.state.reportFilter;
});

const cmpData = computed(function() {
  return store.state.cmpData;
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
  } else {
    reportNotFound.value = true;
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
        treeItem.value = { report: _reports[0] };
      } else {
        reportNotFound.value = true;
      }
    }, _err => {
      console.warn("Failed to get report for hash:", reportHash);
      console.warn(_err);
      reportNotFound.value = true;
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
