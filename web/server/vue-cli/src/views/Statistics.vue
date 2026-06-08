<template>
  <splitpanes
    class="default-theme height-constraint"
  >
    <pane
      size="20"
      :style="{ 'min-width': '300px' }"
    >
      <ReportFilter
        v-fill-height
        :namespace="namespace"
        :show-remove-filtered-reports="false"
        :report-count="reportCount"
        :show-diff-type="false"
        :show-compare-to="showCompareTo"
        :refresh-filter="refreshFilterState"
        @refresh="refresh"
        @set-refresh-filter-state="setRefreshFilterState"
      />
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

        <keep-alive>
          <router-view
            :key="$route.name"
            :bus="bus"
            :namespace="namespace"
            @refresh-filter="setRefreshFilterState(true)"
          />
        </keep-alive>
      </div>
    </pane>
  </splitpanes>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
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

const namespace = "statistics";

const tabs = [
  {
    name: "Product Overview",
    icon: "mdi-briefcase-outline",
    to: { name: "product-overview" },
    showCompareTo: true
  },
  {
    name: "Checker Statistics",
    icon: "mdi-card-account-details",
    to: { name: "checker-statistics" },
    showCompareTo: true
  },
  {
    name: "Severity Statistics",
    icon: "mdi-speedometer",
    to: { name: "severity-statistics" },
    showCompareTo: true
  },
  {
    name: "Component Statistics",
    icon: "mdi-puzzle-outline",
    to: { name: "component-statistics" },
    showCompareTo: true
  },
  {
    name: "Checker Coverage",
    icon: "mdi-clipboard-check-outline",
    to: { name: "checker-coverage-statistics" },
    showCompareTo: false
  },
  {
    name: "Guideline Statistics",
    icon: "mdi-clipboard-text-outline",
    to: { name: "guideline-statistics" },
    showCompareTo: false
  },
];

const refreshFilterState = ref(false);
const reportCount = ref(0);
const showCompareTo = ref(true);
const tab = ref(null);

const bus = mitt();

const refreshTabs = tabs.reduce((map, _tab) => {
  const _resolve = router.resolve(_tab.to);
  if (_resolve.route?.name) {
    map[_resolve.route.name] = false;
  }
  return map;
}, {});

const runIds = computed(function() {
  return store.getters[`${namespace}/getRunIds`];
});

const reportFilter = computed(function() {
  return store.getters[`${namespace}/getReportFilter`];
});

watch(() => tab.value, async () => {
  if (tab.value == null) return;

  const currentTab = tabs[tab.value];
  if (!currentTab) return;

  showCompareTo.value = currentTab.showCompareTo;

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
</script>

<style lang="scss" scoped>
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
</style>
