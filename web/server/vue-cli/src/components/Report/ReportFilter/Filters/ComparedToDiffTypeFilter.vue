<template>
  <select-option
    :id="id"
    title="Diff type"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :loading="baseSelectOptionFilter.loading.value"
    :multiple="false"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="clear(true)"
    @input="baseSelectOptionFilter.setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <v-icon color="grey">
        {{ item.icon }}
      </v-icon>
    </template>

    <template v-slot:no-items>
      <v-list-item>
        <template v-slot:prepend>
          <v-icon>mdi-alert-outline</v-icon>
        </template>
        <v-list-item-title>
          At least one run should be selected at Compare to!
        </v-list-item-title>
      </v-list-item>
    </template>
  </select-option>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { CompareData, DiffType } from "@cc/report-server-types";
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
baseSelectOptionFilter.encodeValue.value = encodeValue;
baseSelectOptionFilter.decodeValue.value = decodeValue;
baseSelectOptionFilter.titleFormatter.value = titleFormatter;
baseSelectOptionFilter.getIconClass.value = getIconClass;

const id = "diff-type";
baseSelectOptionFilter.id.value = id;

const defaultValues = ref([ encodeValue(DiffType.NEW) ]);

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function encodeValue(diffType) {
  switch (parseInt(diffType)) {
  case DiffType.NEW:
    return "New";
  case DiffType.RESOLVED:
    return "Resolved";
  case DiffType.UNRESOLVED:
    return "Unresolved";
  default:
    console.warn("Non existing diff type code: ", diffType);
    return "Unknown";
  }
}

function decodeValue(diffTypeStr) {
  return DiffType[diffTypeStr.replace(" ", "_").toUpperCase()];
}

function updateReportFilter() {
  let diffTypeVal = baseSelectOptionFilter.selectedItems.value.id;
  if (Array.isArray(baseSelectOptionFilter.selectedItems.value) &&
      baseSelectOptionFilter.selectedItems.value.length !== 0) {
    diffTypeVal = baseSelectOptionFilter.selectedItems.value[0].id;
  }
  baseSelectOptionFilter.setCmpData({
    diffType: diffTypeVal
  });
}

function onCmpDataChange(key) {
  if (key === "diff-type") return;
  baseSelectOptionFilter.update();
}

function getIconClass(id) {
  switch (id) {
  case DiffType.NEW:
    return "mdi-set-right";
  case DiffType.RESOLVED:
    return "mdi-set-left";
  case DiffType.UNRESOLVED:
    return "mdi-set-all";
  default:
    console.warn("Unknown diff type: ", id);
  }
}

function fetchItems() {
  baseSelectOptionFilter.loading.value = true;

  if (
    !baseSelectOptionFilter.cmpData.value ||
    !(
      baseSelectOptionFilter.cmpData.value.runIds ||
      baseSelectOptionFilter.cmpData.value.runTag ||
      baseSelectOptionFilter.cmpData.value.openReportsDate
    )
  ) {
    baseSelectOptionFilter.loading.value = false;
    return Promise.resolve([]);
  }

  const _query = Object.keys(DiffType).map(key => {
    const _cmpData = new CompareData(baseSelectOptionFilter.cmpData.value);
    _cmpData.diffType = DiffType[key];

    return new Promise(resolve => {
      ccService.getClient().getRunResultCount(
        baseSelectOptionFilter.runIds.value,
        baseSelectOptionFilter.reportFilter.value,
        _cmpData,
        handleThriftError(res => {
          resolve({ [key]: res });
        }));
    });
  });

  return new Promise(resolve => {
    Promise.all(_query).then(res => {
      resolve(Object.keys(DiffType).map((key, index) => {
        const _id = DiffType[key];
        return {
          id: _id,
          title: titleFormatter(_id),
          count: res[index][key].toNumber(),
          icon: getIconClass(_id)
        };
      }));
      baseSelectOptionFilter.loading.value = false;
    });
  });
}

function titleFormatter(diffType) {
  switch (diffType) {
  case DiffType.NEW:
    return "Only in Compare to";
  case DiffType.RESOLVED:
    return "Only in Baseline";
  case DiffType.UNRESOLVED:
    return "Both in Baseline and Compare to";
  default:
    return "Unknown";
  }
}

// Override the default clear function because one item has to be always
// selected for this filter.
function clear() {}

defineExpose({
  beforeInit: baseSelectOptionFilter.beforeInit,
  afterInit: baseSelectOptionFilter.afterInit,
  update: baseSelectOptionFilter.update,
  registerWatchers: baseSelectOptionFilter.registerWatchers,
  unregisterWatchers: baseSelectOptionFilter.unregisterWatchers,
  initByUrl: baseSelectOptionFilter.initByUrl,
  getUrlState: baseSelectOptionFilter.getUrlState,

  id,
  encodeValue,
  decodeValue,
  updateReportFilter,
  onCmpDataChange,
  defaultValues,
  clear,
  fetchItems
});
</script>
