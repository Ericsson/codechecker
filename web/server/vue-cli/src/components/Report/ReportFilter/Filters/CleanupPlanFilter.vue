<template>
  <manage-cleanup-plan-dialog
    v-model="dialog"
  >
    <select-option
      :id="id"
      title="Cleanup plan"
      :bus="baseSelectOptionFilter.bus"
      :fetch-items="fetchItems"
      :selected-items="baseSelectOptionFilter.selectedItems.value"
      :loading="baseSelectOptionFilter.loading.value"
      :panel="baseSelectOptionFilter.panel.value"
      @clear="baseSelectOptionFilter.clear(true)"
      @input="baseSelectOptionFilter.setSelectedItems"
    >
      <template v-slot:prepend-toolbar-items>
        <v-btn
          v-if="administrating"
          class="manage-cleanup-plan-btn"
          icon="mdi-pencil"
          variant="plain"
          size="small"
          @click.stop="dialog = true"
        >
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </template>

      <template v-slot:icon>
        <v-icon color="grey">
          mdi-sign-direction
        </v-icon>
      </template>
    </select-option>
  </manage-cleanup-plan-dialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, ref, toRef, watch } from "vue";
import { useStore } from "vuex";

import {
  ManageCleanupPlanDialog
} from "@/components/Report/CleanupPlan";

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

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

const id = "cleanup-plan";
baseSelectOptionFilter.id.value = id;

const dialog = ref(false);
const store = useStore();
const currentProduct = computed(() => store.getters.currentProduct);
const administrating = computed(() => {
  return currentProduct.value?.administrating;
});

watch(dialog, value => {
  if (value) return;

  // If the source component manager dialog is closed we need to update
  // the filter items to make sure that new items will be shown.
  baseSelectOptionFilter.bus.emit("update");
});

function updateReportFilter() {
  baseSelectOptionFilter.setReportFilter({
    cleanupPlanNames: 
      baseSelectOptionFilter.selectedItems.value.map(item => item.id)
  });
}

function onReportFilterChange(key) {
  if (key === "cleanupPlanNames") return;
  baseSelectOptionFilter.update();
}

function fetchItems() {
  baseSelectOptionFilter.loading.value = true;

  return new Promise(resolve => {
    ccService.getClient().getCleanupPlans(null, handleThriftError(res => {
      resolve(res.map(cleanupPlan => {
        return {
          id : cleanupPlan.name,
          title: cleanupPlan.name,
          value: cleanupPlan.description
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
