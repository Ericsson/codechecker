<template>
  <v-card
    variant="flat"
    rounded="0"
  >
    <AnalyzerStatisticsDialog
      v-model="analyzerStatisticsDialog"
      :run-id="selectedRunId"
      :run-history-id="selectedRunHistoryId"
    />

    <AnalysisInfoDialog
      v-model="analysisInfoDialog"
      :run-id="selectedRunId"
      :run-history-id="selectedRunHistoryId"
    />

    <v-data-table-server
      v-model="selected"
      v-model:page="page"
      v-model:items-per-page="itemsPerPage"
      v-model:sort-by="sortBy"
      v-model:expanded="expanded"
      v-model:items-per-page-options="itemsPerPageOptions"
      :items-length="totalItems"
      :headers="headers"
      :items="runs"
      :loading="loading"
      loading-text="Loading runs..."
      :must-sort="true"
      show-select
      show-expand
      :mobile-breakpoint="1000"
      item-value="runId"
      return-object
    >
      <template v-slot:top>
        <RunFilterToolbar
          :selected="selected"
          :selected-baseline-runs="selectedBaselineRuns"
          :selected-baseline-tags="selectedBaselineTags"
          :selected-compared-to-runs="selectedComparedToRuns"
          :selected-compared-to-tags="selectedComparedToTags"
          @on-run-filter-changed="onRunFilterChanged"
          @on-run-history-filter-changed="onRunHistoryFilterChanged"
          @update="fetchRuns"
          @delete-complete="selected = []"
        />
      </template>

      <template v-slot:expanded-row="{ columns, item }">
        <tr>
          <td
            v-if="item.$history"
            :colspan="columns.length"
          >
            <expanded-run
              v-model:selected-baseline-tags="selectedBaselineTags"
              v-model:selected-compared-to-tags="selectedComparedToTags"
              :histories="item.$history.values"
              :run="item"
              :open-analysis-info-dialog="openAnalysisInfoDialog"
              :open-analyzer-statistics-dialog="openAnalyzerStatisticsDialog"
            >
              <v-btn
                v-if="item.$history.hasMore"
                class="load-more-btn mb-4"
                color="primary"
                :loading="loadingMoreRunHistories"
                @click="loadMoreRunHistory(item)"
              >
                Load more (+{{ item.$history.limit }})
              </v-btn>
            </expanded-run>
          </td>
        </tr>
      </template>

      <template #item.name="{ item }">
        <run-name-column
          :run-id="item.runId"
          :name="item.name"
          :description="item.description"
          :version-tag="item.versionTag"
          :detection-status-count="item.detectionStatusCount"
          :report-filter-query="getReportFilterQuery(item)"
          :statistics-filter-query="getStatisticsFilterQuery(item)"
          :open-analysis-info-dialog="openAnalysisInfoDialog"
        />
      </template>

      <template #item.analyzerStatistics="{ item }">
        <analyzer-statistics-btn
          v-if="Object.keys(item.analyzerStatistics).length"
          :value="item.analyzerStatistics"
          :show-dividers="false"
          tag="div"
          @click="openAnalyzerStatisticsDialog(item)"
        />
      </template>

      <template #item.runDate="{ item }">
        <v-chip
          class="ma-2"
          color="primary"
          variant="outlined"
        >
          <v-icon left>
            mdi-calendar-range
          </v-icon>
          {{ prettifyDate(item.runDate) }}
        </v-chip>
      </template>

      <template #item.duration="{ item }">
        <v-chip
          class="ma-2"
          color="success"
          variant="outlined"
        >
          <v-icon start>
            mdi-clock-outline
          </v-icon>
          {{ item.$duration }}
        </v-chip>
      </template>

      <template #item.codeCheckerVersion="{ item }">
        <span :title="item.codeCheckerVersion">
          {{ item.$codeCheckerVersion }}
        </span>
      </template>

      <template #item.diff="{ item }">
        <v-container class="py-0">
          <v-row class="flex-nowrap py-0">
            <v-checkbox
              v-model="selectedBaselineRuns"
              :value="item.name"
              class="ma-0"
              hide-details
              multiple
            />

            <v-checkbox
              v-model="selectedComparedToRuns"
              :value="item.name"
              class="ma-0"
              hide-details
              multiple
            />
          </v-row>
        </v-container>
      </template>
    </v-data-table-server>
  </v-card>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";

import { useVersion } from "@/composables/useVersion";

import { ccService, handleThriftError } from "@cc-api";
import {
  Order,
  RunSortMode,
  RunSortType
} from "@cc/report-server-types";

import {
  AnalyzerStatisticsBtn,
  AnalyzerStatisticsDialog,
  ExpandedRun,
  RunFilterToolbar,
  RunNameColumn
} from "@/components/Run";

const { prettifyCCVersion } = useVersion();

const route = useRoute();
const router = useRouter();
const store = useStore();

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

const initialized = ref(false);
const analysisInfoDialog = ref(false);
const totalItems = ref(0);
const loading = ref(false);
const selected = ref([]);
const selectedBaselineRuns = ref([]);
const selectedBaselineTags = ref([]);
const selectedComparedToRuns = ref([]);
const selectedComparedToTags = ref([]);
const analyzerStatisticsDialog = ref(false);
const selectedRunId = ref(null);
const selectedRunHistoryId = ref(null);
const expanded = ref([]);
const loadingMoreRunHistories = ref(false);
const runs = ref([]);

const headers = ref([
  {
    title: "",
    key: "data-table-expand"
  },
  {
    title: "Name",
    key: "name",
    sortable: true
  },
  {
    title: "Number of unresolved reports",
    key: "resultCount",
    align: "center",
    sortable: true
  },
  {
    title: "Analyzer statistics",
    key: "analyzerStatistics",
    sortable: false
  },
  {
    title: "Latest storage date",
    key: "runDate",
    align: "center",
    sortable: true
  },
  {
    title: "Analysis duration",
    key: "duration",
    align: "center",
    sortable: true
  },
  {
    title: "CodeChecker version",
    key: "codeCheckerVersion",
    align: "center",
    sortable: true
  },
  {
    title: "Diff",
    key: "diff",
    align: "center",
    sortable: false,
    width: "100px"
  }
]);

const runFilter = computed(() => store.getters["run/runFilter"]);
const runHistoryFilter = computed(() => store.getters["run/runHistoryFilter"]);

watch(
  [ page, itemsPerPage, sortBy ],
  () => {
    updateUrl();
    if (initialized.value) {
      fetchRuns();
    }
  }, { deep: true }
);

watch(expanded, (newVal, oldVal) => {
  const added = newVal.find(item => !oldVal.includes(item));

  if (added) {
    runExpanded(added);
  } else {
    updateExpandedUrlParam();
  }
});

onMounted(async () => {
  await fetchRuns();
  await initExpandedItems();

  initialized.value = true;
});

function onRunFilterChanged() {
  if (page.value !== 1) {
    page.value = 1;
  } else {
    fetchRuns();
  }
}

async function onRunHistoryFilterChanged() {
  loading.value = true;

  await Promise.all(expanded.value.map(async run => {
    const { limit, offset } = run.$history;

    const { runHistory, hasMore } =
      await getRunHistory(run.runId.toNumber(), limit, offset);

    run.$history.hasMore = hasMore;
    run.$history.values = runHistory;
  }));

  loading.value = false;
}

async function initExpandedItems() {
  const _expanded = route.query["expanded"];
  if (!_expanded)
    return;

  const expandedItems = JSON.parse(_expanded);
  for (const [ key, val ] of Object.entries(expandedItems)) {
    const limit = val.limit;
    const offset = val.offset;
    const runId = +key;

    const run = runs.value.find(r => r.runId.toNumber() === runId);
    const { runHistory, hasMore } =
      await getRunHistory(runId, limit + offset, 0);

    run.$history = {
      limit,
      offset,
      hasMore,
      values: runHistory
    };

    expanded.value.push(run);
  }
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

function updateExpandedUrlParam() {
  const _expanded = expanded.value.reduce((expandedMap, run) => {
    if (run?.$history) {
      expandedMap[run.runId] = {
        limit: run.$history.limit,
        offset: run.$history.offset
      };
    }

    return expandedMap;
  }, {});

  updateUrl({
    expanded: expanded.value.length ? JSON.stringify(_expanded) : undefined
  });
}

async function loadMoreRunHistory(run) {
  loadingMoreRunHistories.value = true;

  const limit = run.$history.limit;

  const offset = run.$history.offset + limit;
  run.$history.offset = offset;

  const { runHistory, hasMore } =
    await getRunHistory(run.runId.toNumber(), limit, offset);

  run.$history.hasMore = hasMore;
  run.$history.values.push(...runHistory);

  updateExpandedUrlParam();

  loadingMoreRunHistories.value = false;
}

async function runExpanded(run, limit=10, offset=0) {
  // Check if given item has any history added to it.
  // Simply update the url params if so.
  if (run.$history) {
    return nextTick(updateExpandedUrlParam);
  }

  loading.value = true;

  const { runHistory, hasMore } =
    await getRunHistory(run.runId.toNumber(), limit, offset);

  run.$history = {
    limit,
    offset,
    hasMore,
    values: runHistory
  };

  updateExpandedUrlParam();

  loading.value = false;
}

async function getRunHistory(runId, limit=10, offset=0) {
  return new Promise(resolve => {
    ccService.getClient().getRunHistory([ runId ], limit, offset,
      runHistoryFilter.value, handleThriftError(runHistory => {
        resolve({
          hasMore: runHistory.length === limit,
          runHistory: runHistory.map(h => ({
            ...h,
            $codeCheckerVersion:
              prettifyCCVersion(h.codeCheckerVersion)
          }))
        });
      }));
  });
}

function getSortMode() {
  let type = null;
  const _sortBy = sortBy.value?.[0]?.key;

  switch (_sortBy) {
  case "name":
    type = RunSortType.NAME;
    break;
  case "resultCount":
    type = RunSortType.UNRESOLVED_REPORTS;
    break;
  case "duration":
    type = RunSortType.DURATION;
    break;
  case "codeCheckerVersion":
    type = RunSortType.CC_VERSION;
    break;
  default:
    type = RunSortType.DATE;
  }

  const _ord = sortBy.value?.[0]?.order === "asc" ? Order.ASC : Order.DESC;

  return new RunSortMode({ type: type, ord: _ord });
}

async function fetchRuns() {
  loading.value = true;

  // Get total item count.
  ccService.getClient().getRunCount(runFilter.value,
    handleThriftError(_totalItems => {
      totalItems.value = _totalItems.toNumber();
    }));

  // Get the runs.
  const limit = itemsPerPage.value;
  const offset = limit * (page.value - 1);
  const sortMode = getSortMode();

  return new Promise(_resolve => {
    ccService.getClient().getRunData(runFilter.value, limit, offset, sortMode,
      handleThriftError(_runs => {
        runs.value = _runs.map(_r => {
          const version = prettifyCCVersion(_r.codeCheckerVersion);

          // Init run history by the expanded array.
          const oldRun = expanded.value.find(_e =>
            _e.runId.toNumber() === _r.runId.toNumber());

          return {
            ..._r,
            $history: oldRun ? oldRun.$history : null,
            $duration: prettifyDuration(_r.duration),
            $codeCheckerVersion: version
          };
        });

        loading.value = false;

        _resolve(runs);
      }));
  });
}

function openAnalysisInfoDialog(runId, runHistoryId=null) {
  selectedRunId.value = runId;
  selectedRunHistoryId.value = runHistoryId;
  analysisInfoDialog.value = true;
}

function openAnalyzerStatisticsDialog(report, history=null) {
  selectedRunId.value = report ? report.runId : null;
  selectedRunHistoryId.value = history ? history.id : null;
  analyzerStatisticsDialog.value = true;
}

function prettifyDuration(seconds) {
  if (seconds >= 0) {
    const durHours = Math.floor(seconds / 3600);
    const durMins  = Math.floor(seconds / 60) - durHours * 60;
    const durSecs  = seconds - durMins * 60 - durHours * 3600;

    const prettyDurHours = (durHours < 10 ? "0" : "") + durHours;
    const prettyDurMins  = (durMins  < 10 ? "0" : "") + durMins;
    const prettyDurSecs  = (durSecs  < 10 ? "0" : "") + durSecs;

    return prettyDurHours + ":" + prettyDurMins + ":" + prettyDurSecs;
  }

  return "";
}

function getReportFilterQuery(run) {
  return {
    run: run.name
  };
}

function getStatisticsFilterQuery(run) {
  return {
    run: run.name
  };
}

function prettifyDate(date) {
  if (!date) return "";
  const d = new Date(date);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hours = String(d.getHours()).padStart(2, "0");
  const minutes = String(d.getMinutes()).padStart(2, "0");
  const seconds = String(d.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}
</script>

<style lang="scss" scoped>
.v-data-table :deep(tbody tr.v-data-table__expanded__content) {
  box-shadow: none;
}
</style>
