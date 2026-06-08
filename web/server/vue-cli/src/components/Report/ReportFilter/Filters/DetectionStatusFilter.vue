<template>
  <select-option
    :id="id.value"
    title="Latest Detection Status"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :loading="baseSelectOptionFilter.loading.value"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="baseSelectOptionFilter.clear(true)"
    @input="baseSelectOptionFilter.setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <detection-status-icon :status="item.id" />
    </template>

    <template v-slot:append-toolbar-title>
      <tooltip-help-icon
        class="mr-2"
      >
        Filter reports by the <b>latest</b> detection status.<br><br>

        The detection status is the latest state of a bug report in a run. When
        a report id is first detected it will be marked as <b>New</b>. When the
        reports stored again with the same run name then the detection status
        can change to one of the following options:
        <ul>
          <li>
            <b>Resolved:</b> when the bug report can't be found after the
            subsequent storage.
          </li>
          <li>
            <b>Unresolved:</b> when the bug report is still among the results
            after the subsequent storage.
          </li>
          <li>
            <b>Reopened:</b> when a resolved bug appears again.
          </li>
          <li>
            <b>Off:</b> were reported by a checker that is switched off
            during the last analysis which results were stored.
          </li>
          <li>
            <b>Unavailable:</b> were reported by a checker that does not
            exists anymore because it was removed or renamed.
          </li>
        </ul>
      </tooltip-help-icon>

      <tooltip-help-icon
        v-if="reportFilter?.isUnique"
        class="mr-2"
      >
        <template v-slot:activator="{ props: activatorProps }">
          <v-icon
            v-bind="activatorProps"
            color="error"
          >
            mdi-alert
          </v-icon>
        </template>

        Not available in uniqueing mode! Several detection statuses could
        belong to the same bug!
      </tooltip-help-icon>

      <SelectedToolbarTitleItems
        v-if="baseSelectOptionFilter.selectedItems.value"
        :value="baseSelectOptionFilter.selectedItems.value"
      />
    </template>
  </select-option>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, ref, toRef } from "vue";

import { DetectionStatusIcon } from "@/components/Icons";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { DetectionStatus, ReportFilter } from "@cc/report-server-types";

import {
  useBaseSelectOptionFilter
} from "@/composables/useBaseSelectOptionFilter";
import { useDetectionStatus } from "@/composables/useDetectionStatus";
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

const id = ref("detection-status");
// eslint-disable-next-line vue/no-ref-object-reactivity-loss
baseSelectOptionFilter.id.value = id.value;

const reportFilter = computed(
  () => baseSelectOptionFilter.baseFilter?.reportFilter?.value
);

const {
  detectionStatusFromStringToCode,
  detectionStatusFromCodeToString
} = useDetectionStatus();

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function encodeValue(detectionStatusId) {
  return detectionStatusFromCodeToString(detectionStatusId);
}

function decodeValue(detectionStatusName) {
  return detectionStatusFromStringToCode(detectionStatusName);
}

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    detectionStatus: 
      baseSelectOptionFilter.selectedItems.value.map(item => item.id)
  });
}

function onReportFilterChange(key) {
  if (key === "detectionStatus") return;
  baseSelectOptionFilter.update();
}

function fetchItems() {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  _reportFilter.detectionStatus = null;

  return new Promise(resolve => {
    ccService.getClient().getDetectionStatusCounts(
      baseSelectOptionFilter.runIds.value,
      _reportFilter,
      baseSelectOptionFilter.cmpData.value,
      handleThriftError(res => {
        resolve(Object.keys(DetectionStatus).map(status => {
          const _id = DetectionStatus[status];
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
