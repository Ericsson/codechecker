<template>
  <div>
    <div 
      class="mt-2 mb-2 d-flex align-center justify-space-between w-100 p-1"
    >
      <ClearAllFilters
        :namespace="namespace"
        @clear="clearAllFilters"
      />
      <ReportCount :value="reportCount" />
    </div>

    <v-divider />

    <div>
      <unique-filter
        :ref="setFilterRef"
        :namespace="namespace"
        @update:url="updateUrl"
      />
    </div>

    <v-divider />

    <v-list
      density="compact"
      :border="false"
      :rounded="false"
      elevation="0"
    >
      <v-list-item class="pl-0 border-sm border-solid border-opacity">
        <v-expansion-panels
          v-model="activeBaselinePanelId"
          eager
        >
          <v-expansion-panel>
            <v-expansion-panel-title
              class="pa-0 px-1"
              expand-icon="mdi-chevron-down"
              collapse-icon="mdi-chevron-up"
            >
              <b>BASELINE</b>
            </v-expansion-panel-title>
            <v-expansion-panel-text class="pa-1">
              <baseline-run-filter
                :ref="setFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />

              <v-divider />

              <baseline-open-reports-date-filter
                :ref="setFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list-item>

      <v-list-item
        v-if="showCompareTo"
        class="pl-0 border-sm border-solid border-opacity border-t-0"
      >
        <v-expansion-panels
          v-model="activeCompareToPanelId"
          hover
          eager
        >
          <v-expansion-panel>
            <v-expansion-panel-title
              class="pa-0 px-1 primary--text"
              expand-icon="mdi-chevron-down"
              collapse-icon="mdi-chevron-up"
            >
              <b>COMPARE TO</b>
            </v-expansion-panel-title>
            <v-expansion-panel-text class="pa-1">
              <compared-to-run-filter
                :ref="setFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />

              <v-divider />

              <compared-to-open-reports-date-filter
                :ref="setFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />

              <v-divider v-if="showDiffType" />

              <compared-to-diff-type-filter
                v-if="showDiffType"
                :ref="setFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list-item>

      <v-list-item class="pl-1">
        <file-path-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <checker-name-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <severity-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <report-status-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider v-if="showReviewStatus" />

      <v-list-item
        v-if="showReviewStatus"
        class="pl-1"
      >
        <review-status-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <detection-status-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <analyzer-name-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <source-component-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <cleanup-plan-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <checker-message-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-list-item class="pl-0 border-sm border-solid border-opacity">
        <v-expansion-panels
          v-model="activeDatePanelId"
          hover
          eager
        >
          <v-expansion-panel>
            <v-expansion-panel-title
              class="pa-0 px-1"
            >
              <b>Dates</b>
            </v-expansion-panel-title>
            <v-expansion-panel-text class="pa-1">
              <detection-date-filter
                id="detection-date-filter"
                :ref="setFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />

              <v-divider class="mt-2" />

              <fix-date-filter
                id="fix-date-filter"
                :ref="setFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list-item>

      <v-list-item class="pl-1">
        <report-hash-filter
          id="report-hash-filter"
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <bug-path-length-filter
          id="bug-path-length-filter"
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <testcase-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>
    </v-list>

    <v-divider v-if="showRemoveFilteredReports" />

    <div
      v-if="showRemoveFilteredReports"
      class="mt-2 mb-2 d-flex align-center justify-center w-100 p-1"
    >
      <remove-filtered-reports
        class="mt-4 w-100"
        :namespace="namespace"
        @update="updateAllFilters"
      />
    </div>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  toRef,
  watch
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";

import {
  AnalyzerNameFilter,
  BaselineOpenReportsDateFilter,
  BaselineRunFilter,
  BugPathLengthFilter,
  CheckerMessageFilter,
  CheckerNameFilter,
  CleanupPlanFilter,
  ComparedToDiffTypeFilter,
  ComparedToOpenReportsDateFilter,
  ComparedToRunFilter,
  DetectionDateFilter,
  DetectionStatusFilter,
  FilePathFilter,
  FixDateFilter,
  ReportHashFilter,
  ReportStatusFilter,
  ReviewStatusFilter,
  SeverityFilter,
  SourceComponentFilter,
  TestcaseFilter,
  UniqueFilter
} from "./Filters";

import { useBaseFilter } from "@/composables/useBaseFilter";

import ClearAllFilters from "./ClearAllFilters";
import RemoveFilteredReports from "./RemoveFilteredReports";
import ReportCount from "./ReportCount";

const props = defineProps({
  namespace: { type: String, required: true },
  showCompareTo: { type: Boolean, default: true },
  showReviewStatus: { type: Boolean, default: true },
  showRemoveFilteredReports: { type: Boolean, default: true },
  showDiffType: { type: Boolean, default: true },
  reportCount: { type: Number, required: true },
  refreshFilter: { type: Boolean, default: false }
});

const emit = defineEmits([ "set-refresh-filter-state", "refresh" ]);

const activeBaselinePanelId = ref(0);
const activeCompareToPanelId = ref(0);
const activeDatePanelId = ref(0);
const filters = ref([]);

const setFilterRef = el => {
  if (el && !filters.value.includes(el)) {
    filters.value.push(el);
  }
};

const {
  reportFilterUnwatch,
  runIdsUnwatch,
  cmpDataUnwatch
} = useBaseFilter(toRef(props, "namespace"));

const route = useRoute();
const router = useRouter();
const store = useStore();

const reportFilter = computed(() => store.state[props.namespace].reportFilter);

watch(() => props.refreshFilter, state => {
  if (!state) return;
  
  initByUrl();
  emit("set-refresh-filter-state", false);
});

onMounted(() => {
  nextTick(() => {
    initByUrl();
  });
});

function beforeInit() {
  unregisterWatchers();
}

function afterInit() {
  emit("refresh");
  registerWatchers();
}

function updateUrl() {
  const _filters = filters.value;

  if (!_filters?.length) {
    return;
  };

  const _states = _filters
    .filter(filter => filter?.getUrlState)
    .map(filter => filter?.getUrlState?.());

  const _queryParams = Object.assign({}, route.query, ..._states);
  router.replace({ query: _queryParams }).catch(() => {});
}

function registerWatchers() {
  unregisterWatchers();

  reportFilterUnwatch.value = store.watch(
    state => state[props.namespace].reportFilter, () => {
      emit("refresh");
    }, { deep: true });

  runIdsUnwatch.value = store.watch(
    state => state[props.namespace].runIds, () => {
      emit("refresh");
    });

  cmpDataUnwatch.value = store.watch(
    state => state[props.namespace].cmpData, () => {
      emit("refresh");
    }, { deep: true });
}

function unregisterWatchers() {
  if (reportFilterUnwatch.value) reportFilterUnwatch.value();
  if (runIdsUnwatch.value) runIdsUnwatch.value();
  if (cmpDataUnwatch.value) cmpDataUnwatch.value();
}

function initByUrl() {
  const _filters = filters.value;
  if (!_filters?.length) {
    return;
  };

  // Before init.
  beforeInit();
  _filters.forEach(filter => {
    if (filter?.beforeInit) filter?.beforeInit?.();
  });

  // Init all filters by URL parameters.
  const _results = _filters
    .filter(filter => filter?.initByUrl)
    .map(filter => filter?.initByUrl?.());

  // If all filters are initalized call a post function.
  Promise.all(_results).then(() => {
    _filters.forEach(filter => {
      if (filter?.afterInit) filter?.afterInit?.();
    });
    afterInit();

    preparePanelsOnInit();
  });
}

function preparePanelsOnInit() {
  if (!reportFilter.value.date) {
    activeDatePanelId.value = undefined;
  }
}

async function clearAllFilters() {
  const _filters = filters.value;
  if (!_filters?.length) return;

  // Unregister watchers.
  unregisterWatchers();
  _filters.forEach(filter => filter?.unregisterWatchers?.());

  // Clear all filters and update the url.
  await Promise.all(_filters.map(filter => filter?.clear?.(false)));
  updateUrl();

  // Update filters after clear.
  updateAllFilters();

  // Register watchers.
  _filters.forEach(filter => filter?.registerWatchers?.());
  registerWatchers();
}

function updateAllFilters() {
  const _filters = filters.value;
  if (!_filters?.length) return;

  _filters.forEach(filter => filter?.update?.() );

  emit("refresh");
}

onBeforeUnmount(() => {
  unregisterWatchers();

  const _filters = filters.value;
  if (_filters?.length) {
    _filters.forEach(filter => filter?.unregisterWatchers?.());
  }
});
</script>

<style lang="scss">
.v-list-item {
  min-height: 40px !important;
  padding-top: 2px !important;
  padding-bottom: 2px !important;
}

.v-expansion-panel--active > .v-expansion-panel-title,
.v-expansion-panel-title {
  min-height: 40px;
}

.v-expansion-panel-text > .v-expansion-panel-text__wrap {
  padding: 0 4px 0 6px;
}

#baseline-filters,
#compare-to-filters,
#date-filters {
  border: 1px solid rgba(0, 0, 0, 0.12);
}

#compare-to-filters {
  border-top: 0;
}

.v-expansion-panel-title {
  min-height: 48px !important;
  font-size: 0.875rem !important;
}

.v-expansion-panel-title__icon {
  order: 1;
}
.v-expansion-panel-title header {
  order: 2;
}
</style>
