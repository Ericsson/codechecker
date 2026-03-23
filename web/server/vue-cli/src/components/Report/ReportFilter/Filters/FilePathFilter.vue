<template>
  <select-option
    :id="id"
    title="File path"
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
        mdi-file-document-outline
      </v-icon>
    </template>

    <template v-slot:append-toolbar>
      <AnywhereOnReportPath v-model="isAnywhere" />
    </template>
  </select-option>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter } from "@cc/report-server-types";
import { ref, toRef, watch } from "vue";

import {
  useBaseSelectOptionFilter
} from "@/composables/useBaseSelectOptionFilter";
import SelectOption from "./SelectOption/SelectOption";

import { useRoute } from "vue-router";
import AnywhereOnReportPath from "./SelectOption/AnywhereOnReportPath.vue";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([ "update:url" ]);

const baseSelectOptionFilter =
  useBaseSelectOptionFilter(toRef(props, "namespace"));

baseSelectOptionFilter.fetchItems.value = fetchItems;
baseSelectOptionFilter.updateReportFilter.value = updateReportFilter;

const id = "filepath";
baseSelectOptionFilter.id.value = id;

const isAnywhere = ref(false);

const anywhereId = "anywhere-filepath";

const search = ref(
  {
    placeHolder: "Search for files (e.g.: */src/*)...",
    regexLabel: "Filter by wildcard pattern (e.g.: */src/*)",
    filterItems: baseSelectOptionFilter.filterItems
  }
);
const route = useRoute();

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

watch(isAnywhere, () => {
  // Update the global reportFilter object in baseFilter.
  updateReportFilter();

  // Emit update url trigger to ReportFilter.
  emit("update:url");

  // Fetch items based on the filter set.
  baseSelectOptionFilter.update();
});

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    filepath: baseSelectOptionFilter.selectedItems.value.map(item => item.id),
    fileMatchesAnyPoint: isAnywhere.value
  });
}

function onReportFilterChange(key) {
  if (key === "filepath") return;
  baseSelectOptionFilter.update();
}

function getUrlState() {
  const state =
    baseSelectOptionFilter.selectedItems.value.map(
      item => baseSelectOptionFilter.encodeValue.value(item.id)
    );

  return {
    [id]: state.length ? state : undefined,
    [anywhereId]: isAnywhere.value || undefined
  };
}

function initByUrl() {
  isAnywhere.value = !!route.query[anywhereId];
  baseSelectOptionFilter.initByUrl();
}

function fetchItems(opt={}) {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  _reportFilter.filepath = opt.query;

  const _limit = opt.limit || baseSelectOptionFilter.defaultLimit.value;
  const _offset = 0;

  return new Promise(resolve => {
    ccService.getClient().getFileCounts(
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
        }).map(file => {
          return {
            id : file,
            title: file,
            count: res[file]?.toNumber() || 0
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

  id,
  updateReportFilter,
  onReportFilterChange,
  getUrlState,
  initByUrl,
  fetchItems
});
</script>

<style lang="scss" scoped>
.filter-item-title {
  direction: rtl;
  text-align: left;
}
</style>