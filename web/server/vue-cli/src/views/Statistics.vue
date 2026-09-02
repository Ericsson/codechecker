<template>
  <splitpanes
    class="default-theme height-constraint"
  >
    <pane
      size="20"
      :style="{ 'min-width': '300px' }"
    >
      <div v-fill-height>
        <ReportFilter
          :show-remove-filtered-reports="false"
          :report-count="reportCount"
          :refresh-filter="refreshFilterState"
          :hidden-filters="hiddenFilters"
          @refresh="refresh"
          @set-refresh-filter-state="setRefreshFilterState"
        />
      </div>
    </pane>
    <pane>
      <div v-fill-height>
        <v-tabs
          v-model="tab"
        >
          <v-tab
            v-for="t in tabs"
            :key="t.name"
            :to="{ ...t.to, query: {
              ...$route.query
            }}"
            class="mx-2"
            exact
          >
            <v-icon class="mr-2">
              {{ t.icon }}
            </v-icon>
            {{ t.name }}
          </v-tab>
        </v-tabs>

        <router-view v-slot="{ Component }">
          <keep-alive>
            <component
              :is="Component"
              :key="$route.name"
              :bus="bus"
              @refresh-filter="setRefreshFilterState(true)"
            />
          </keep-alive>
        </router-view>
      </div>
    </pane>
  </splitpanes>
</template>

<script setup>
import {
  computed,
  nextTick,
  onActivated,
  onDeactivated,
  onMounted,
  onUnmounted,
  ref,
  watch
} from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import { Pane, Splitpanes } from "splitpanes";
import mitt from "mitt";

import { ccService, handleThriftError } from "@cc-api";

import { FillHeight } from "@/directives";
import { ReportFilter } from "@/components/Report/ReportFilter";

const vFillHeight = FillHeight;

const router = useRouter();
const store = useStore();

const tabs = [
  {
    name: "Product Overview",
    icon: "mdi-briefcase-outline",
    to: { name: "product-overview" },
    hiddenFiltersByTab: []
  },
  {
    name: "Checker Statistics",
    icon: "mdi-card-account-details",
    to: { name: "checker-statistics" },
    hiddenFiltersByTab: []
  },
  {
    name: "Severity Statistics",
    icon: "mdi-speedometer",
    to: { name: "severity-statistics" },
    hiddenFiltersByTab: []
  },
  {
    name: "Component Statistics",
    icon: "mdi-puzzle-outline",
    to: { name: "component-statistics" },
    hiddenFiltersByTab: []
  },
  {
    name: "Checker Coverage",
    icon: "mdi-clipboard-check-outline",
    to: { name: "checker-coverage-statistics" },
    hiddenFiltersByTab: [
      "baseline-open-reports-date-filter",
      "group:compareTo",
      "file-path-filter",
      "checker-name-filter",
      "severity-filter",
      "report-status-filter",
      "review-status-filter",
      "detection-status-filter",
      "analyzer-name-filter",
      "source-component-filter",
      "cleanup-plan-filter",
      "checker-message-filter",
      "group:dateFilter",
      "report-hash-filter",
      "bug-path-length-filter",
      "testcase-filter"
    ]
  },
  {
    name: "Guideline Statistics",
    icon: "mdi-clipboard-text-outline",
    to: { name: "guideline-statistics" },
    hiddenFiltersByTab: [
      "baseline-open-reports-date-filter",
      "group:compareTo",
      "file-path-filter",
      "checker-name-filter",
      "severity-filter",
      "report-status-filter",
      "review-status-filter",
      "detection-status-filter",
      "analyzer-name-filter",
      "source-component-filter",
      "cleanup-plan-filter",
      "checker-message-filter",
      "group:dateFilter",
      "report-hash-filter",
      "bug-path-length-filter",
      "testcase-filter"
    ]
  },
];

const refreshFilterState = ref(false);
const reportCount = ref(0);
const tab = ref(null);

const bus = mitt();

const refreshTabs = tabs.reduce((map, _tab) => {
  const _resolve = router.resolve(_tab.to);
  if (_resolve.route?.name) {
    map[_resolve.route.name] = false;
  }
  return map;
}, {});

const hiddenFilters = ref([]);
const baseHiddenFilters = ref([ "compared-to-diff-type-filter" ]);

const runIds = computed(function() {
  return store.getters.getRunIds;
});

const reportFilter = computed(function() {
  return store.getters.getReportFilter;
});

watch(() => tab.value, async () => {
  // FIXME: At page reload, this
  // event triggers, but the report filter
  // is not ready yet.

  if (tab.value == null) return;

  const currentTab = tabs[tab.value];
  if (!currentTab) return;

  hiddenFilters.value = [
    ...baseHiddenFilters.value,
    ...currentTab.hiddenFiltersByTab
  ];

  await nextTick();
  refreshCurrentTab();
});

function refresh() {
  ccService.getClient().getRunResultCount(
    runIds.value,
    reportFilter.value,
    null,
    handleThriftError(_res => {
      reportCount.value = _res.toNumber();
    }));

  tabs.forEach(_tab => {
    const _resolve = router.resolve(_tab.to);
    if (_resolve.route?.name) {
      refreshTabs[_resolve.route.name] = true;
    }
  });

  refreshCurrentTab();
}

function refreshCurrentTab() {
  bus.emit("refresh");

  if (tab.value == null) return;

  const currentTab = tabs[tab.value];
  if (!currentTab) return;

  const _resolve = router.resolve(currentTab.to);
  if (_resolve.route?.name) {
    refreshTabs[_resolve.route.name] = false;
  }
}

function setRefreshFilterState(state) {
  refreshFilterState.value = state;
}

function lockBodyScroll() {
  document.body.style.overflow = "hidden";
}

function unlockBodyScroll() {
  document.body.style.overflow = "";
}

onMounted(lockBodyScroll);
onActivated(lockBodyScroll);
onUnmounted(unlockBodyScroll);
onDeactivated(unlockBodyScroll);
</script>

<style lang="scss" scoped>
.height-constraint {
  height: calc(100vh - 100px);
}

.splitpanes__pane {
  overflow-y: hidden;
  height: 100%;
}

.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}
</style>
