<template>
  <select-option
    :id="id"
    title="Checker name"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :search="search"
    :loading="baseSelectOptionFilter.loading.value"
    :limit="baseSelectOptionFilter.defaultLimit.value"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="baseSelectOptionFilter.clear(true)"
    @input="baseSelectOptionFilter.setSelectedItems"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-card-account-details
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

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

const id = "checker-name";
baseSelectOptionFilter.id.value = id;

const search = ref({
  placeHolder: "Search for checker names (e.g.: core*)...",
  regexLabel: "Filter by wildcard pattern (e.g.: core*)",
  filterItems: baseSelectOptionFilter.filterItems
});

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    checkerName: baseSelectOptionFilter.selectedItems.value.map(item => item.id)
  });
}

function onReportFilterChange(key) {
  if (key === "checkerName") return;
  baseSelectOptionFilter.update();
}

function fetchItems(opt={}) {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  _reportFilter.checkerName = opt.query;

  const _limit = opt.limit || baseSelectOptionFilter.defaultLimit.value;
  const _offset = 0;

  return new Promise(resolve => {
    ccService.getClient().getCheckerCounts(
      baseSelectOptionFilter.runIds.value,
      _reportFilter,
      baseSelectOptionFilter.cmpData.value,
      _limit,
      _offset,
      handleThriftError(res => {
        resolve(res.map(checker => {
          return {
            id: checker.name,
            title: checker.name,
            count: checker.count.toNumber()
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
