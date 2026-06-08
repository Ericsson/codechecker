<template>
  <select-option
    :id="id.value"
    title="Testcase"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :search="search"
    :loading="baseSelectOptionFilter.loading.value"
    :limit="baseSelectOptionFilter.defaultLimit.value"
    :multiple="true"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="baseSelectOptionFilter.clear(true)"
    @input="baseSelectOptionFilter.setSelectedItems"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-card-account-details
      </v-icon>
    </template>
    <template v-slot:title="{ item }">
      <v-list-item-title
        class="mr-1 filter-item-title"
        :title="`\u200E${item.title}`"
      >
        &lrm;{{ item.title }}&lrm;
      </v-list-item-title>
    </template>
  </select-option>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { Pair, ReportFilter } from "@cc/report-server-types";
import { ref, toRef } from "vue";

import { useBaseSelectOptionFilter }
  from "@/composables/useBaseSelectOptionFilter";
import SelectOption from "./SelectOption/SelectOption";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([ "update:url" ]);

const baseSelectOptionFilter =
  useBaseSelectOptionFilter(toRef(props, "namespace"));
baseSelectOptionFilter.fetchItems.value = fetchItems;
baseSelectOptionFilter.updateReportFilter.value = updateReportFilter;

const id = ref("testcase");
// eslint-disable-next-line vue/no-ref-object-reactivity-loss
baseSelectOptionFilter.id.value = id.value;

const search = ref({
  placeHolder: "Search for testcase names...",
  regexLabel: "Filter by wildcard pattern",
  filterItems: baseSelectOptionFilter.filterItems
});

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    annotations: baseSelectOptionFilter.selectedItems.value.length == 0
      ? null : baseSelectOptionFilter.selectedItems.value.map(
        item => new Pair({
          first: "testcase",
          second: item.id
        })
      )
  });
}

function onReportFilterChange(key) {
  if (key === "testcaseName") return;
  baseSelectOptionFilter.update();
}

function fetchItems(opt={}) {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter =
    new ReportFilter(baseSelectOptionFilter.reportFilter.value);
  _reportFilter.annotations = opt.query ? opt.query.map(q => new Pair({
    first: "testcase",
    second: q
  })) : [ new Pair({
    first: "testcase",
    second: null 
  }) ];

  return new Promise(resolve => {
    ccService.getClient().getReportAnnotations(
      baseSelectOptionFilter.runIds.value,
      _reportFilter,
      baseSelectOptionFilter.cmpData.value,
      handleThriftError(res => {
        resolve(res.map(annotation => {
          return {
            id: annotation,
            title: annotation
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

<style lang="scss" scoped>
.filter-item-title {
  direction: rtl;
  text-align: left;
}
</style>