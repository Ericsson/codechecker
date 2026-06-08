<template>
  <splitpanes
    class="default-theme height-constraint"
  >
    <pane size="20" :style="{ 'min-width': '320px' }">
      <ReportFilter
        :namespace="namespace"
        :report-count="totalItems"
        @refresh="refresh"
      />
    </pane>
    <pane>
      <checker-documentation-dialog
        v-model="checkerDocDialog"
        :checker="selectedChecker"
      />
      <v-data-table-server
        v-model="selected"
        v-model:page="page"
        v-model:items-per-page="itemsPerPage"
        v-model:sort-by="sortBy"
        v-model:expanded="expanded"
        :items-per-page-options="itemsPerPageOptions"
        :items-length="totalItems"
        :headers="tableHeaders"
        :items="formattedReports"
        :loading="loading"
        loading-text="Loading reports..."
        :must-sort="true"
        show-select
        :mobile-breakpoint="1100"
        item-value="id"
        return-object
        @update:expanded="itemExpanded"
      >
        <template v-slot:top>
          <v-toolbar
            flat
            class="report-filter-toolbar"
            density="compact"
            color="transparent"
          >
            <div class="d-flex justify-end w-100">
              <set-cleanup-plan-btn :selected-reports="selected" />
            </div>
          </v-toolbar>
        </template>

        <template v-slot:expanded-row="{ item }">
          <td
            class="pa-0"
            :colspan="headers.length"
          >
            <v-list v-if="expandedItemsHistory[item.id]">
              <v-list-item
                v-for="report in expandedItemsHistory[item.id]"
                :key="report.reportId.toNumber()"
                density="compact"
              >
                <v-list-item-title>
                  Same report in
                  <kbd class="text-kbd">{{ report.$runName }}</kbd> run:
                  <span>
                    <detection-status-icon
                      :status="parseInt(report.detectionStatus)"
                      :title="report.$detectionStatusTitle"
                      :size="18"
                    />
                    <review-status-icon
                      :status="parseInt(report.reviewData.status)"
                      :size="18"
                    />
                    <router-link
                      :to="{ name: 'report-detail', query: {
                        ...route.query,
                        'report-id': report.reportId,
                        'report-hash': undefined
                      }}"
                    >
                      {{ report.checkedFile }}:{{ report.line }}
                    </router-link>
                  </span>
                </v-list-item-title>
              </v-list-item>
            </v-list>

            <v-card
              v-else
              flat
              tile
            >
              <v-card-text>
                Loading...
                <v-progress-linear
                  indeterminate
                  class="mb-0"
                />
              </v-card-text>
            </v-card>
          </td>
        </template>

        <template #item.bugHash="{ item }">
          <span :title="item.bugHash">
            {{ truncate(item.bugHash, 10) }}
          </span>
        </template>

        <template #item.checkedFile="{ item }">
          <router-link
            :to="{ name: 'report-detail', query: {
              ...route.query,
              'report-id': item.reportId ? item.reportId : undefined,
              'report-hash': item.bugHash,
              'report-filepath': reportFilter.isUnique
                ? `*${item.checkedFile}` : item.checkedFile
            }}"
            class="file-name"
          >
            {{ item.checkedFile }}
            <span v-if="item.line">@&nbsp;Line&nbsp;{{ item.line }}</span>
          </router-link>
        </template>

        <template #item.checkerId="{ item }">
          <span
            class="checker-name primary--text"
            @click="openCheckerDocDialog(item.checkerId, item.analyzerName)"
          >
            {{ item.checkerId }}
          </span>
        </template>

        <template #item.checkerMsg="{ item }">
          <span class="checker-message">
            {{ item.checkerMsg }}
          </span>
        </template>

        <template #item.severity="{ item }">
          <severity-icon :status="item.severity" />
        </template>

        <template #item.bugPathLength="{ item }">
          <v-chip :color="getBugPathLenColor(item.bugPathLength)">
            {{ item.bugPathLength }}
          </v-chip>
        </template>

        <template
          v-if="reportFilter.isUnique"
          #item.reviewData="{ item }"
        >
          <review-status-icon
            v-for="status in sameReports[item.bugHash]"
            :key="status"
            :status="parseInt(status)"
            class="pa-1"
          />
        </template>

        <template v-else #item.reviewData="{ item }">
          <review-status-icon :status="parseInt(item.reviewData.status)" />
        </template>

        <template #item.detectionStatus="{ item }">
          <detection-status-icon
            :status="parseInt(item.detectionStatus)"
            :title="item.$detectionStatusTitle"
          />
        </template>
      </v-data-table-server>
    </pane>
  </splitpanes>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";
import { Pane, Splitpanes } from "splitpanes";

import { ccService, handleThriftError } from "@cc-api";
import { Checker, Order, SortMode, SortType } from "@cc/report-server-types";

import { useBugPathLenColor } from "@/composables/useBugPathLenColor";
import { useDetectionStatus } from "@/composables/useDetectionStatus";
import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";

import CheckerDocumentationDialog from
  "@/components/CheckerDocumentationDialog";
import { ReportFilter } from "@/components/Report/ReportFilter";
import { SetCleanupPlanBtn } from "@/components/Report/CleanupPlan";

const namespace = "report";

const route = useRoute();
const router = useRouter();
const store = useStore();
const bugPathLenColor = useBugPathLenColor();
const detectionStatus = useDetectionStatus();

const itemsPerPageOptions = [
  { value: 25, title: "25" },
  { value: 50, title: "50" },
  { value: 100, title: "100" },
  { value: -1, title: "$vuetify.dataFooter.itemsPerPageAll" }
];
const page = ref(parseInt(route.query["page"]) || 1);
const itemsPerPage = ref(
  parseInt(route.query["items-per-page"]) ||
  itemsPerPageOptions[0].value
);

const sortBy = ref(
  route.query["sort-by"] 
    ? [ { 
      key: route.query["sort-by"], 
      order: route.query["sort-desc"] === "true" ? "desc" : "asc" 
    } ]
    : [ { key: "name", order: "asc" } ]
);

const headers = [
  {
    title: "",
    value: "data-table-expand"
  },
  {
    title: "Report hash",
    value: "bugHash",
    sortable: false
  },
  {
    title: "File",
    value: "checkedFile",
    sortable: true
  },
  {
    title: "Message",
    value: "checkerMsg",
    sortable: false
  },
  {
    title: "Checker name",
    value: "checkerId",
    sortable: true
  },
  {
    title: "Analyzer",
    value: "analyzerName",
    align: "center",
    sortable: false
  },
  {
    title: "Severity",
    value: "severity",
    sortable: true
  },
  {
    title: "Bug path length",
    value: "bugPathLength",
    align: "center",
    sortable: true
  },
  {
    title: "Latest review status",
    value: "reviewData",
    align: "center",
    sortable: true
  },
  {
    title: "Latest detection status",
    value: "detectionStatus",
    align: "center",
    sortable: true
  },
  {
    title: "Timestamp",
    value: "timestamp",
    align: "center",
    sortable: true
  },
  {
    title: "Chronological order",
    value: "chronological_order",
    align: "center",
    sortable: true
  },
  {
    title: "Testcase",
    value: "testcase",
    align: "center",
    sortable: true
  }
];

const reports = ref([]);
const sameReports = ref({});
const hasTimeStamp = ref(true);
const hasTestCase = ref(true);
const hasChronologicalOrder = ref(true);
const selected = ref([]);
const totalItems = ref(0);
const loading = ref(false);
const initalized = ref(false);
const checkerDocDialog = ref(false);
const selectedChecker = ref(null);
const expanded = ref([]);
const expandedItemsHistory = ref({});
const runIdsUnwatch = ref(null);
const reportFilterUnwatch = ref(null);
const cmpDataUnwatch = ref(null);

const runIds = computed(function() {
  return store.getters[`${namespace}/getRunIds`];
});

const reportFilter = computed(function() {
  return store.getters[`${namespace}/getReportFilter`];
});

const cmpData = computed(function() {
  return store.getters[`${namespace}/getCmpData`];
});

const tableHeaders = computed(function() {
  if (!headers || !reportFilter.value) return [];

  return headers.filter(_header => {
    if (_header.value === "detectionStatus") {
      return !reportFilter.value.isUnique;
    }

    if (_header.value === "data-table-expand") {
      return reportFilter.value.isUnique;
    }

    if (_header.value === "timestamp") {
      return hasTimeStamp.value &&
        !reportFilter.value.isUnique;
    }

    if (_header.value === "testcase") {
      return hasTestCase.value &&
        !reportFilter.value.isUnique;
    }

    if (_header.value === "chronological_order") {
      return hasChronologicalOrder.value &&
        !reportFilter.value.isUnique;
    }

    return true;
  });
});

const formattedReports = computed(function() {
  return reports.value.map(_report => {
    const _reportId = _report.reportId ? _report.reportId.toString() : "";
    const _id = _reportId + _report.bugHash;

    const _detectionStatus =
      detectionStatus.detectionStatusFromCodeToString(_report.detectionStatus);
    const _detectedAt = _report.detectedAt
      ? prettifyDate(_report.detectedAt) : null;
    const _fixedAt = _report.fixedAt
      ? prettifyDate(_report.fixedAt) : null;

    const _detectionStatusTitle = [
      `Status: ${_detectionStatus}`,
      ...(_detectedAt ? [ `Detected at: ${_detectedAt}` ] : []),
      ...(_fixedAt ? [ `Fixed at: ${_fixedAt}` ] : [])
    ].join("\n");

    return {
      ..._report,
      "$detectionStatusTitle": _detectionStatusTitle,
      "id": _id,
      "sameReports": _report.sameReports,
      "timestamp": _report.annotations["timestamp"],
      "testcase": _report.annotations["testcase"],
      "chronological_order": _report.annotations["chronological_order"]
    };
  });
});

watch(
  [ page, itemsPerPage, sortBy ],
  () => {
    updateUrl();
    if (initalized.value) {
      fetchReports();
    }
  },
  { deep: true }
);

watch(
  formattedReports,
  () => {
    hasTimeStamp.value =
      formattedReports.value.some(_report => _report.timestamp);

    hasTestCase.value =
      formattedReports.value.some(_report => _report.testcase);

    hasChronologicalOrder.value =
      formattedReports.value.some(_report => _report["chronological_order"]);
  }
);

function itemExpanded(expandedItems) {
  if (!expandedItems || expandedItems.length === 0) return;

  for (const item of expandedItems) {
    if (
      !(item.id in expandedItemsHistory.value) ||
      expandedItemsHistory.value[item.id].length === 0
    ) {
      ccService.getSameReports(item.bugHash).then(_sameReports => {
        const report = reports.value.find(report =>
          (report.reportId?.toString() || "") + report.bugHash === item.id
        );
        if (report) {
          expandedItemsHistory.value[item.id] = _sameReports;
        }
      });
    }
  }
}

function getSortMode() {
  let _type = null;
  const _sortBy = sortBy.value?.[0]?.key;

  switch (_sortBy) {
  case "checkedFile":
    _type = SortType.FILENAME;
    break;
  case "checkerId":
    _type = SortType.CHECKER_NAME;
    break;
  case "detectionStatus":
    _type = SortType.DETECTION_STATUS;
    break;
  case "reviewData":
    _type = SortType.REVIEW_STATUS;
    break;
  case "bugPathLength":
    _type = SortType.BUG_PATH_LENGTH;
    break;
  case "timestamp":
    _type = SortType.TIMESTAMP;
    break;
  case "testcase":
    _type = SortType.TESTCASE;
    break;
  case "chronological_order":
    _type = SortType.CHRONOLOGICAL_ORDER;
    break;
  default:
    _type = SortType.SEVERITY;
  }

  const _ord = sortBy.value?.[0]?.order === "asc" ? Order.ASC : Order.DESC;

  return [ new SortMode({ type: _type, ord: _ord }) ];
}

function openCheckerDocDialog(checkerId, analyzerName) {
  selectedChecker.value = new Checker({
    checkerId: checkerId,
    analyzerName: analyzerName
  });
  checkerDocDialog.value = true;
}

function updateUrl() {
  const _defaultItemsPerPage = itemsPerPageOptions[0].value;
  const _itemsPerPage =
    itemsPerPage.value === _defaultItemsPerPage
      ? undefined
      : itemsPerPage;

  const _page = page.value === 1 ? undefined : page.value;
  const _sortBy = sortBy.value?.[0]?.key;
  const _sortDesc = sortBy.value?.[0]?.order === "desc";

  router.replace({
    query: {
      ...route.query,
      "items-per-page": _itemsPerPage,
      "page": _page,
      "sort-by": _sortBy,
      "sort-desc": _sortDesc,
    }
  }).catch(() => {});
}

function refresh() {
  expanded.value = [];

  ccService.getClient().getRunResultCount(
    runIds.value,
    reportFilter.value,
    cmpData.value,
    handleThriftError(_res => {
      totalItems.value = _res.toNumber();
    }));

  if (page.value !== 1 && initalized.value) {
    page.value = 1;
  } else {
    fetchReports();
  }
}

function fetchReports() {
  loading.value = true;

  const _limit = itemsPerPage.value;
  const _offset = _limit * (page.value - 1);
  const _sortType = getSortMode();
  const _getDetails = false;

  ccService.getClient().getRunResults(
    runIds.value,
    _limit,
    _offset,
    _sortType,
    reportFilter.value,
    cmpData.value,
    _getDetails,
    handleThriftError(_reports => {
      reports.value = _reports;
      loading.value = false;
      initalized.value = true;

      _reports.forEach(_report => {
        ccService.getSameReports(_report.bugHash).then(_sameReports => {
          sameReports.value[_report.bugHash] =
            [
              ...new Set(_sameReports.map(_r => _r.reviewData.status))
            ];
        });
      });
    }));
}

function truncate(text, length) {
  if (!text) return "";
  if (text.length <= length) return text;
  return text.substring(0, length) + "...";
}

function prettifyDate(date) {
  if (!date) return "";
  const _d = new Date(date);
  const _year = _d.getFullYear();
  const _month = String(_d.getMonth() + 1).padStart(2, "0");
  const _day = String(_d.getDate()).padStart(2, "0");
  const _hours = String(_d.getHours()).padStart(2, "0");
  const _minutes = String(_d.getMinutes()).padStart(2, "0");
  const _seconds = String(_d.getSeconds()).padStart(2, "0");
  return `${_year}-${_month}-${_day} ${_hours}:${_minutes}:${_seconds}`;
}

function getBugPathLenColor(length) {
  return bugPathLenColor.getBugPathLenColor(length);
}

function registerWatchers() {
  unregisterWatchers();

  runIdsUnwatch.value = watch(runIds, () => {
    refresh();
  });

  reportFilterUnwatch.value = watch(reportFilter, () => {
    refresh();
  }, { deep: true });

  cmpDataUnwatch.value = watch(cmpData, () => {
    refresh();
  }, { deep: true });
}

function unregisterWatchers() {
  runIdsUnwatch.value?.();
  reportFilterUnwatch.value?.();
  cmpDataUnwatch.value?.();
}

onMounted(() => {
  registerWatchers();
  refresh();
});

onBeforeUnmount(() => {
  unregisterWatchers();
});
</script>

<style lang="scss">

body {
  overflow: hidden;
}

.height-constraint {
  height: calc(100vh - 100px);
}

.splitpanes__pane {
  overflow-y: auto;
  height: 100%;
}

.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}

.v-data-table {
  .file-name,
  .checker-name,
  .checker-message {
    word-break: break-word;
  }

  .checker-name {
    cursor: pointer;
  }
}

kbd {
  background-color: #eeeeee;
  border-radius: 3px;
  border: 1px solid #b4b4b4;
  color: #333333;
  display: inline-block;
  font-size: 0.85em;
  font-weight: bold;
  line-height: 1;
  padding: 2px 4px;
  white-space: nowrap;
}
</style>
