<template>
  <filter-toolbar
    title="Report hash filter"
    :panel="baseFilter.panel"
    @clear="clear(true)"
  >
    <template v-slot:append-toolbar-title>
      <span
        v-if="reportHash"
        class="selected-items"
        :title="reportHash"
      >
        ({{ reportHash }})
      </span>
    </template>

    <v-card-actions class="">
      <v-text-field
        :id="id"
        :model-value="reportHash"
        append-icon="mdi-magnify"
        label="Search for report hash (min 5 characters)..."
        single-line
        hide-details
        variant="outlined"
        clearable
        density="compact"
        @update:model-value="setReportHash"
      />
    </v-card-actions>
  </filter-toolbar>
</template>

<script setup>
import { useBaseFilter } from "@/composables/useBaseFilter";
import { ref, toRef } from "vue";
import { useRoute } from "vue-router";
import FilterToolbar from "./Layout/FilterToolbar";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([ "update:url" ]);
const id = "report-hash";
const reportHash = ref(null);

const baseFilter = useBaseFilter(toRef(props, "namespace"));

const route = useRoute();

function setReportHash(_reportHash, _updateUrl=true) {
  reportHash.value = _reportHash;
  updateReportFilter();

  if (_updateUrl) {
    emit("update:url");
  }
}

function updateReportFilter() {
  baseFilter.setReportFilter({
    reportHash: reportHash.value ? [ `${reportHash.value}*` ] : null
  });
}

function getUrlState() {
  return {
    [id]: reportHash.value ? reportHash.value : undefined
  };
}

function initByUrl() {
  return new Promise(resolve => {
    const _state = route.query[id];
    if (_state) {
      setReportHash(_state, false);
    }

    resolve();
  });
}

function initPanel() {
  baseFilter.panel.value = reportHash.value !== null;
}

function clear(updateUrl) {
  setReportHash(null, updateUrl);
}

defineExpose({
  beforeInit: baseFilter.beforeInit,
  afterInit: baseFilter.afterInit,
  registerWatchers: baseFilter.registerWatchers,
  unregisterWatchers: baseFilter.unregisterWatchers,

  id,
  updateReportFilter,
  getUrlState,
  initByUrl,
  initPanel,
  clear
});
</script>
