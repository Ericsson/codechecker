<template>
  <select-option
    :id="id.value"
    title="Analyzer name"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :search="search"
    :loading="baseSelectOptionFilter.loading.value"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="baseSelectOptionFilter.clear(true)"
    @input="baseSelectOptionFilter.setSelectedItems"
  >
    <template #icon>
      <v-icon color="grey">
        mdi-crosshairs
      </v-icon>
    </template>
  </select-option>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter } from "@cc/report-server-types";
import { ref, toRef } from "vue";

import {
  useBaseSelectOptionFilter
} from "@/composables/useBaseSelectOptionFilter";
import SelectOption from "./SelectOption/SelectOption";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([ "update:url" ]);

const baseSelectOptionFilter =
  useBaseSelectOptionFilter(toRef(props, "namespace"));
baseSelectOptionFilter.fetchItems.value = fetchItems;
baseSelectOptionFilter.updateReportFilter.value = updateReportFilter;


const id = ref("analyzer-name");
// eslint-disable-next-line vue/no-ref-object-reactivity-loss
baseSelectOptionFilter.id.value = id.value;

const search = ref({
  placeHolder: "Search for analyzer names (e.g.: clang*)...",
  regexLabel: "Filter by wildcard pattern (e.g.: clang*)",
  filterItems: []
});

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    analyzerNames:
      baseSelectOptionFilter.selectedItems.value.map(item => item.id)
  });
}

function onReportFilterChange(key) {
  if (key === "analyzerNames") return;
  baseSelectOptionFilter.update();
}

function fetchItems(opt={}) {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  _reportFilter.analyzerNames = opt.query;

  const _limit = opt.limit || baseSelectOptionFilter.defaultLimit.value;
  const _offset = 0;

  return new Promise(resolve => {
    ccService.getClient().getAnalyzerNameCounts(
      baseSelectOptionFilter.runIds.value,
      _reportFilter,
      baseSelectOptionFilter.cmpData.value,
      _limit,
      _offset,
      handleThriftError(res => {
      // Order the results alphabetically.
        resolve(Object.keys(res).sort((a, b) => {
          if (a < b) return -1;
          if (a > b) return 1;
          return 0;
        }).map(analyzerName => {
          return {
            id : analyzerName,
            title: analyzerName,
            count : res[analyzerName]
          };
        }));
        baseSelectOptionFilter.loading.value = false;
      }));
  });
}

defineExpose({
  beforeInit: baseSelectOptionFilter.beforeInit,
  afterInit: baseSelectOptionFilter.afterInit,
  clear: baseSelectOptionFilter.clear,
  update: baseSelectOptionFilter.update,
  registerWatchers: baseSelectOptionFilter.registerWatchers,
  unregisterWatchers: baseSelectOptionFilter.unregisterWatchers,
  initByUrl: baseSelectOptionFilter.initByUrl,
  getUrlState: baseSelectOptionFilter.getUrlState,

  id,
  updateReportFilter,
  onReportFilterChange,
  fetchItems
});
</script>
