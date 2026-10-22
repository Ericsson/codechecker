<template>
  <v-container fluid>
    <v-col>
      <v-row class="ma-0 mb-4">
        <h3 class="title text-primary">
          <v-btn
            color="primary"
            variant="outlined"
            :disabled="!files.length"
            @click="downloadCSV"
          >
            Export CSV
          </v-btn>

          <v-btn
            icon="mdi-refresh"
            title="Reload statistics"
            color="primary"
            variant="text"
            @click="fetchStatistics"
          />
          <tooltip-help-icon
            color="primary"
            size="x-large"
          >
            The tab shows the test coverage which was stored with a run.
            <br><br>
            The coverage of one run is shown at a time. If exactly one run is
            selected in the left "Run / Tag Filter" menu, its coverage is
            shown. Otherwise the run can be chosen on this page from the
            selected runs (or from all runs if the filter is empty).
            <br><br>
            Test coverage data can be created from LCOV tracefiles by the
            <strong>report-converter</strong> tool.
          </tooltip-help-icon>
        </h3>
      </v-row>

      <v-row class="ma-0 mb-4" align="center">
        <v-autocomplete
          v-if="runs.length > 1"
          :model-value="selectedRunId"
          :items="runs"
          item-title="name"
          item-value="runId"
          label="Run"
          prepend-inner-icon="mdi-run-fast"
          variant="outlined"
          density="compact"
          class="run-selector mr-4"
          hide-details
          @update:model-value="selectRun"
        />
        <span v-else-if="selectedRun" class="text-subtitle-1 mr-4">
          <v-icon class="mr-1">mdi-run-fast</v-icon>
          Run: <strong>{{ selectedRun.name }}</strong>
        </span>

        <test-coverage-summary
          v-if="files.length"
          :counts="counts"
        />
      </v-row>

      <v-progress-linear
        v-if="loading && !files.length"
        indeterminate
        class="mb-4"
      />

      <v-alert
        v-if="error"
        type="error"
        variant="tonal"
      >
        {{ error }}
      </v-alert>

      <v-alert
        v-else-if="!loading && !files.length"
        type="info"
        variant="tonal"
      >
        <template v-if="selectedRun">
          No test coverage data is stored for run
          <strong>{{ selectedRun.name }}</strong>.
        </template>
        <template v-else>
          No run is available.
        </template>
        See the
        <a :href="docUrl" target="_blank" rel="noopener">documentation</a>
        on how to store test coverage.
      </v-alert>

      <v-row v-else-if="files.length" class="ma-0">
        <test-coverage-file-view
          v-if="fileId !== null"
          :run-id="selectedRunId"
          :file-id="fileId"
          :file-coverage="fileCoverage"
          :back-link="backLink"
        />
        <test-coverage-table
          v-else
          v-model:search="search"
          :items="items"
          :breadcrumbs="breadcrumbs"
          :loading="loading"
          :get-directory-link="getDirectoryLink"
          :get-file-link="getFileLink"
        />
      </v-row>
    </v-col>
  </v-container>
</template>

<script setup>
import { computed, onActivated, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ccService, handleThriftError } from "@cc-api";
import {
  Order,
  RunFilter,
  RunSortMode,
  RunSortType
} from "@cc/report-server-types";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { useBaseStatistics } from "@/composables/useBaseStatistics";
import { useToCSV } from "@/composables/useToCSV";

import {
  buildCoverageTree,
  findDirectory,
  getBreadcrumbs,
  getDirectoryItems,
  getDirectoryOfFile,
  normalizeFileCoverage,
  summarize,
  toCSVRows
} from "./coverage-tree";
import TestCoverageFileView from "./TestCoverageFileView";
import TestCoverageSummary from "./TestCoverageSummary";
import TestCoverageTable from "./TestCoverageTable";

const props = defineProps({
  bus: { type: Object, required: true }
});

const ROUTE_NAME = "test-coverage-statistics";
const RUN_QUERY = "coverage-run";
const DIR_QUERY = "coverage-dir";
const FILE_QUERY = "coverage-file";

const docUrl = "https://github.com/Ericsson/codechecker/blob/master/docs/" +
  "tools/report-converter.md#supported-test-coverage-outputs";

const route = useRoute();
const router = useRouter();
const csv = useToCSV();
const baseStats = useBaseStatistics(props, null);

const runs = ref([]);
const files = ref([]);
const loading = ref(false);
const error = ref(null);
const search = ref("");

// Identifies the latest coverage request so older results are ignored.
let requestId = 0;
// The run of the latest coverage request.
let requestedRunId = null;

const isActive = computed(() => route.name === ROUTE_NAME);

function queryNumber(key) {
  const value = Number(route.query[key]);
  return Number.isInteger(value) && value > 0 ? value : null;
}

const selectedRunId = computed(() => {
  const runId = queryNumber(RUN_QUERY);
  if (runs.value.some(run => run.runId === runId))
    return runId;
  return runs.value.length ? runs.value[0].runId : null;
});

const selectedRun = computed(() =>
  runs.value.find(run => run.runId === selectedRunId.value) || null);

const tree = computed(() => buildCoverageTree(files.value));

const currentDirectory = computed(() =>
  findDirectory(tree.value, route.query[DIR_QUERY]) || tree.value);

const items = computed(() =>
  getDirectoryItems(currentDirectory.value, search.value));

const breadcrumbs = computed(() =>
  getBreadcrumbs(tree.value, currentDirectory.value.path));

const counts = computed(() => summarize(files.value));

const fileId = computed(() => queryNumber(FILE_QUERY));

const fileCoverage = computed(() =>
  files.value.find(file => file.fileId === fileId.value) || null);

const backLink = computed(() => {
  const directory = route.query[DIR_QUERY] ||
    (fileCoverage.value
      ? getDirectoryOfFile(fileCoverage.value.filePath) : undefined);
  return getDirectoryLink(directory);
});

function getDirectoryLink(path) {
  return {
    query: {
      ...route.query,
      [DIR_QUERY]: path && path !== tree.value.path ? path : undefined,
      [FILE_QUERY]: undefined
    }
  };
}

function getFileLink(item) {
  return {
    query: {
      ...route.query,
      [RUN_QUERY]: String(selectedRunId.value),
      [FILE_QUERY]: String(item.fileId)
    }
  };
}

function selectRun(runId) {
  router.push({
    query: {
      ...route.query,
      [RUN_QUERY]: runId ? String(runId) : undefined,
      [DIR_QUERY]: undefined,
      [FILE_QUERY]: undefined
    }
  }).catch(() => {});
}

function getRuns() {
  const runIds = baseStats.runIds.value;
  const runFilter = new RunFilter({
    ids: runIds && runIds.length ? runIds : null
  });
  const sortMode = new RunSortMode({
    type: RunSortType.DATE,
    ord: Order.DESC
  });

  return ccService.getRuns(runFilter, sortMode);
}

function getFileCoverages(runId) {
  return new Promise((resolve, reject) => {
    ccService.getClient().getFileCoverages([ runId ],
      handleThriftError(resolve, reject));
  });
}

async function loadCoverage() {
  const currentRequest = ++requestId;
  const runId = selectedRunId.value;
  requestedRunId = runId;

  loading.value = true;
  error.value = null;

  try {
    const fileCoverages = runId !== null ? await getFileCoverages(runId) : [];
    if (currentRequest !== requestId)
      return;

    files.value = fileCoverages.map(normalizeFileCoverage);
  } catch (err) {
    if (currentRequest !== requestId)
      return;

    files.value = [];
    requestedRunId = null;
    error.value = "Failed to load the test coverage: " +
      (err?.message || err);
  } finally {
    if (currentRequest === requestId)
      loading.value = false;
  }
}

async function fetchStatistics() {
  loading.value = true;
  error.value = null;

  try {
    runs.value = (await getRuns()).map(run => ({
      runId: run.runId.toNumber(),
      name: run.name
    }));
  } catch (err) {
    runs.value = [];
    error.value = "Failed to load the runs: " + (err?.message || err);
    loading.value = false;
    return;
  }

  // The run in the URL is not available anymore (e.g. the run filter was
  // changed), so the directory and file of that run are not valid either.
  const queryRunId = queryNumber(RUN_QUERY);
  if (queryRunId !== null && queryRunId !== selectedRunId.value) {
    router.replace({
      query: {
        ...route.query,
        [RUN_QUERY]: undefined,
        [DIR_QUERY]: undefined,
        [FILE_QUERY]: undefined
      }
    }).catch(() => {});
  }

  await loadCoverage();
}

function downloadCSV() {
  const runName = (selectedRun.value?.name || "run")
    .replace(/[^\w.-]+/g, "_");
  csv.toCSV(
    toCSVRows(files.value), `codechecker_test_coverage_${runName}.csv`);
}

baseStats.setupRefreshListener(fetchStatistics);

watch(selectedRunId, runId => {
  if (isActive.value && runs.value.length && runId !== requestedRunId)
    loadCoverage();
});

watch(() => currentDirectory.value.path, () => {
  search.value = "";
});

onActivated(() => {
  if (runs.value.length && selectedRunId.value !== requestedRunId)
    loadCoverage();
});
</script>

<style lang="scss" scoped>
.run-selector {
  max-width: 400px;
  min-width: 250px;
}
</style>
