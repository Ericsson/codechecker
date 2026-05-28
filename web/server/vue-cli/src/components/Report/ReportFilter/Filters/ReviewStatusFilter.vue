<template>
  <select-option
    :id="id.value"
    title="Latest Review Status"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :loading="baseSelectOptionFilter.loading.value"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="baseSelectOptionFilter.clear(true)"
    @input="baseSelectOptionFilter.setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <review-status-icon :status="item.id" />
    </template>

    <template v-slot:append-toolbar-title>
      <tooltip-help-icon
        class="mr-2"
      >
        Filter reports by the <b>latest</b> review status.<br><br>

        Reports can be assigned a review status of the following values:
        <ul>
          <li>
            <b>Unreviewed</b>: Nobody has seen this report.
          </li>
          <li>
            <b>Confirmed:</b> This is really a bug.
          </li>
          <li>
            <b>False positive:</b> This is not a bug.
          </li>
          <li>
            <b>Intentional:</b> This report is a bug but we don't want to fix
            it.
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

import { ReviewStatusIcon } from "@/components/Icons";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { ReportFilter, ReviewStatus } from "@cc/report-server-types";

import { useBaseSelectOptionFilter }
  from "@/composables/useBaseSelectOptionFilter";
import { useReviewStatus } from "@/composables/useReviewStatus";
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

const id = ref("review-status");
// eslint-disable-next-line vue/no-ref-object-reactivity-loss
baseSelectOptionFilter.id.value = id.value;

const reviewStatus = useReviewStatus();

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function encodeValue(reviewStatusId) {
  return reviewStatus.reviewStatusFromCodeToString(reviewStatusId);
}

function decodeValue(reviewStatusName) {
  return reviewStatus.reviewStatusFromStringToCode(reviewStatusName);
}

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    reviewStatus:
      baseSelectOptionFilter.selectedItems.value.map(item => item.id)
  });
}

function onReportFilterChange(key) {
  if (key === "reviewStatus") return;
  baseSelectOptionFilter.update();
}

function fetchItems() {
  baseSelectOptionFilter.loading.value = true;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  _reportFilter.reviewStatus = null;

  return new Promise(resolve => {
    ccService.getClient().getReviewStatusCounts(
      baseSelectOptionFilter.runIds.value,
      _reportFilter,
      baseSelectOptionFilter.cmpData.value,
      handleThriftError(res => {
        resolve(Object.keys(ReviewStatus).map(status => {
          const _id = ReviewStatus[status];
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
