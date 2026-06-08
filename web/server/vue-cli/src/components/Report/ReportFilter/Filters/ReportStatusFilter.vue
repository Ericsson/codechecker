<template>
  <select-option
    :id="id.value"
    title="Report Status"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :loading="baseSelectOptionFilter.loading.value"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="baseSelectOptionFilter.clear(true)"
    @input="baseSelectOptionFilter.setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <report-status-icon :status="item.id" />
    </template>

    <template v-slot:append-toolbar-title>
      <tooltip-help-icon
        class="mr-2"
      >
        Filter reports by the <b>latest</b> report status.<br><br>

        A report can be outstanding or closed.
        Outstanding reports are potential bugs.
        Closed reports are fixed bugs, suppressed, resolved
        or unavailable reports.

        <br><br>

        The report is <b>outstanding</b> when its
        <ul>
          <li>
            <b>Review status</b>: is unreviewed or confirmed
          </li>
          <b>and</b>
          <li>
            <b>Detection status</b>: is new, unresolved or reopened.
          </li>
        </ul>
        The report is <b>closed</b> when its
        <ul>
          <li>
            <b>Review status</b>: is false positive, intentional
          </li>
          <b>or</b>
          <li>
            <b>Detection status</b>: is resolved, off or unavailable.
          </li>
        </ul>
      </tooltip-help-icon>

      <selected-toolbar-title-items
        v-if="baseSelectOptionFilter.selectedItems.value"
        :value="baseSelectOptionFilter.selectedItems.value"
      />
    </template>
  </select-option>
</template>
  
<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { ref, toRef } from "vue";

import { ReportStatusIcon } from "@/components/Icons";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { ReportFilter, ReportStatus } from "@cc/report-server-types";

import { useBaseSelectOptionFilter }
  from "@/composables/useBaseSelectOptionFilter";
import { useReportStatus } from "@/composables/useReportStatus";
import { SelectOption, SelectedToolbarTitleItems } from "./SelectOption";

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

const id = ref("report-status");
// eslint-disable-next-line vue/no-ref-object-reactivity-loss
baseSelectOptionFilter.id.value = id.value;

const reportStatus = useReportStatus();

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function encodeValue(reportStatusId) {
  return reportStatus.reportStatusFromCodeToString(reportStatusId);
}

function decodeValue(reportStatusName) {
  return reportStatus.reportStatusFromStringToCode(reportStatusName);
}

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    reportStatus:
      baseSelectOptionFilter.selectedItems.value.map(item => item.id)
  });
}

function onReportFilterChange(key) {
  if (key === "reportStatus") return;
  baseSelectOptionFilter.update();
}

function fetchItems() {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  _reportFilter.reportStatus = null;

  return new Promise(resolve => {
    ccService.getClient().getReportStatusCounts(
      baseSelectOptionFilter.runIds.value,
      _reportFilter,
      baseSelectOptionFilter.cmpData.value,
      handleThriftError(res => {
        resolve(Object.keys(ReportStatus).map(status => {
          const _id = ReportStatus[status];
          return {
            id: _id,
            title: encodeValue(_id),
            count: res[_id] !== undefined ? res[_id].toNumber() : 0
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
  