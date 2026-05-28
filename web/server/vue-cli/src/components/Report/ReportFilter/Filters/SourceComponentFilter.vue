<template>
  <manage-source-component-dialog
    v-model="isDialogOpen"
  >
    <select-option
      :id="id.value"
      title="Source component"
      :bus="baseSelectOptionFilter.bus"
      :fetch-items="fetchItems"
      :selected-items="baseSelectOptionFilter.selectedItems.value"
      :search="search"
      :loading="baseSelectOptionFilter.loading.value"
      :panel="baseSelectOptionFilter.panel.value"
      @clear="baseSelectOptionFilter.clear(true)"
      @input="baseSelectOptionFilter.setSelectedItems"
    >
      <template v-slot:append-toolbar>
        <ReportFilterModeSelector v-model="reportFilterMode" />
      </template>
      <template v-slot:prepend-toolbar-items>
        <v-btn
          v-if="administrating"
          class="manage-components-btn"
          icon="mdi-pencil"
          variant="plain"
          size="small"
          @click="isDialogOpen = true"
        />
      </template>

      <template v-slot:icon>
        <v-icon color="grey">
          mdi-puzzle-outline
        </v-icon>
      </template>

      <template v-slot:title="{ item }">
        <source-component-tooltip :value="item.value">
          <template v-slot="{ props: slotProps }">
            <v-list-item-title
              v-bind="slotProps"
              class="mr-1 filter-item-title"
              :title="item.title"
            >
              {{ item.title }}
            </v-list-item-title>
          </template>
        </source-component-tooltip>
      </template>
    </select-option>
  </manage-source-component-dialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, ref, toRef, watch } from "vue";
import { useStore } from "vuex";

import {
  ManageSourceComponentDialog,
  SourceComponentTooltip
} from "@/components/Report/SourceComponent";

import { useBaseSelectOptionFilter }
  from "@/composables/useBaseSelectOptionFilter";
import { useRoute } from "vue-router";
import ReportFilterModeSelector
  from "./SelectOption/ReportFilterModeSelector.vue";
import SelectOption from "./SelectOption/SelectOption";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([ "update:url" ]);

const id = ref("source-component");
const anywhereId = ref("anywhere-sourcecomponent");
const sameOriginId = ref("sameorigin-sourcecomponent");
const isDialogOpen = ref(false);
const reportFilterMode = ref(null);
const isAnywhere = ref(false);
const isSameOrigin = ref(false);

const baseSelectOptionFilter =
  useBaseSelectOptionFilter(toRef(props, "namespace"));
baseSelectOptionFilter.fetchItems.value = fetchItems;
baseSelectOptionFilter.updateReportFilter.value = updateReportFilter;

const search = ref({
  placeHolder : "Search for source components...",
  filterItems: baseSelectOptionFilter.filterItems
});
const store = useStore();
const route = useRoute();

const currentProduct = computed(() => store.getters.currentProduct);

const administrating = computed(() => {
  return currentProduct.value?.administrating;
});

watch(isDialogOpen, value => {
  if (value) return;

  // If the source component manager dialog is closed we need to update
  // the filter items to make sure that new items will be shown.
  baseSelectOptionFilter.bus.emit("update");
});

watch(reportFilterMode, () => {
  if (reportFilterMode.value == "anywhere") {
    isAnywhere.value = true;
    isSameOrigin.value = false;
  } else if (reportFilterMode.value == "single-origin") {
    isAnywhere.value = false;
    isSameOrigin.value = true;
  } else {
    isAnywhere.value = false;
    isSameOrigin.value = false;
  }

  updateReportFilter();
  emit("update:url");
  baseSelectOptionFilter.update();
});

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    componentNames:
      baseSelectOptionFilter.selectedItems.value.map(item => item.id),
    componentMatchesAnyPoint: isAnywhere.value,
    fullReportPathInComponent: isSameOrigin.value
  });
}

function onReportFilterChange(key) {
  if (key === "componentNames") return;
  baseSelectOptionFilter.update();
}

function getUrlState() {
  const _state =
    baseSelectOptionFilter.selectedItems.value.map(
      item => baseSelectOptionFilter.encodeValue.value(item.id)
    );

  return {
    [id.value]: _state.length ? _state : undefined,
    [anywhereId.value]: isAnywhere.value || undefined,
    [sameOriginId.value]: isSameOrigin.value || undefined
  };
}

function setReportFilterMode() {
  if (isAnywhere.value && !isSameOrigin.value) {
    reportFilterMode.value = "anywhere";
  } else if (!isAnywhere.value && isSameOrigin.value) {
    reportFilterMode.value = "single-origin";
  } else {
    reportFilterMode.value = "end";
  }
}

function initByUrl() {
  isAnywhere.value = !!route.query[anywhereId.value];
  isSameOrigin.value = !!route.query[sameOriginId.value];
  setReportFilterMode();
  baseSelectOptionFilter.initCheckOptionsByUrl();
}

function fetchItems(opt={}) {
  baseSelectOptionFilter.loading.value = true;

  return new Promise(resolve => {
    const _filter = opt.query;
    ccService.getClient().getSourceComponents(
      _filter,
      handleThriftError(res => {
        resolve(res.map(component => {
          return {
            id : component.name,
            title: component.name,
            value: component.value || component.description
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
  getUrlState,
  initByUrl,
  onReportFilterChange,
  updateReportFilter,
  fetchItems
});
</script>
