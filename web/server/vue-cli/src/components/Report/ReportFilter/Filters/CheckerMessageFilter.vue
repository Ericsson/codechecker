<template>
  <select-option
    :id="id.value"
    title="Checker message"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :search="search"
    :loading="baseSelectOptionFilter.loading.value"
    :limit="baseSelectOptionFilter.defaultLimit.value"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="baseSelectOptionFilter.clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-message-text-outline
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

const id = ref("checker-msg");
// eslint-disable-next-line vue/no-ref-object-reactivity-loss
baseSelectOptionFilter.id.value = id.value;

const search = ref({
  placeHolder: "Search for checker messages (e.g.: *deref*)...",
  regexLabel: "Filter by wildcard pattern (e.g.: *deref*)",
  filterItems: baseSelectOptionFilter.filterItems
});

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    checkerMsg: baseSelectOptionFilter.selectedItems.value.map(item => item.id)
  });
}

function onReportFilterChange(key) {
  if (key === "checkerMsg") return;
  baseSelectOptionFilter.update();
}

function fetchItems(opt={}) {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  _reportFilter.checkerMsg = opt.query;

  const _limit = opt.limit || baseSelectOptionFilter.defaultLimit.value;
  const _offset = 0;

  return new Promise(resolve => {
    ccService.getClient().getCheckerMsgCounts(
      baseSelectOptionFilter.runIds.value,
      _reportFilter,
      baseSelectOptionFilter.cmpData.value,
      _limit,
      _offset,
      handleThriftError(res => {
        resolve(Object.keys(res).map(msg => {
          return {
            id : msg,
            title: msg,
            count: res[msg].toNumber()
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
