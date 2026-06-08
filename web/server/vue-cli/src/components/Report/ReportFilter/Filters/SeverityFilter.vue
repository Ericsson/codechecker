<template>
  <select-option
    :id="id.value"
    title="Severity"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :loading="baseSelectOptionFilter.loading.value"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="baseSelectOptionFilter.clear(true)"
    @input="baseSelectOptionFilter.setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <severity-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { ref, toRef } from "vue";

import { SeverityIcon } from "@/components/Icons";
import { ReportFilter, Severity } from "@cc/report-server-types";

import { useBaseSelectOptionFilter }
  from "@/composables/useBaseSelectOptionFilter";
import { useSeverity } from "@/composables/useSeverity";
import SelectOption from "./SelectOption/SelectOption";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([ "update:url" ]);

const baseSelectOptionFilter =
  useBaseSelectOptionFilter(toRef(props, "namespace"));
baseSelectOptionFilter.fetchItems.value = fetchItems;
baseSelectOptionFilter.updateReportFilter.value = updateReportFilter;
baseSelectOptionFilter.encodeValue.value = encodeValue;
baseSelectOptionFilter.decodeValue.value = decodeValue;

const id = ref("severity");
// eslint-disable-next-line vue/no-ref-object-reactivity-loss
baseSelectOptionFilter.id.value = id.value;

const severity = useSeverity();

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function encodeValue(severityId) {
  return severity.severityFromCodeToString(severityId);
}

function decodeValue(severityName) {
  return severity.severityFromStringToCode(severityName);
}

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    severity: baseSelectOptionFilter.selectedItems.value.map(item => item.id)
  });
}

function onReportFilterChange(key) {
  if (key === "severity") return;
  baseSelectOptionFilter.update();
}

function fetchItems() {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  _reportFilter.severity = null;

  return new Promise(resolve => {
    ccService.getClient().getSeverityCounts(
      baseSelectOptionFilter.runIds.value,
      _reportFilter,
      baseSelectOptionFilter.cmpData.value,
      handleThriftError(res => {
        resolve(Object.keys(Severity).map(status => {
          const _severityId = Severity[status];
          const _count =
            res[_severityId] !== undefined ? res[_severityId].toNumber() : 0;

          return {
            id: _severityId,
            title: encodeValue(_severityId),
            count: _count
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
  encodeValue,
  decodeValue,
  updateReportFilter,
  onReportFilterChange,
  fetchItems
});
</script>
