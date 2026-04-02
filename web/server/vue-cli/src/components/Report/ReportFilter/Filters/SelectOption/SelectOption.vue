<template>
  <FilterToolbar
    :title="title"
    :panel="panel"
    @clear="emit('clear')"
  >
    <template v-slot:append-toolbar-title>
      <slot name="append-toolbar-title">
        <SelectedToolbarTitleItems
          :value="selectedItems"
        />
      </slot>
    </template>

    <template v-slot:prepend-toolbar-title>
      <slot name="prepend-toolbar-title" />
    </template>

    <template v-slot:prepend-toolbar-items>
      <slot name="prepend-toolbar-items" />
    </template>

    <template v-slot:append-toolbar-items>
      <v-menu
        v-model="menu"
        content-class="settings-menu"
        :close-on-content-click="false"
        :nudge-width="300"
        :max-width="600"
        offset-x
      >
        <v-progress-linear
          v-if="loading"
          indeterminate
          size="64"
        />

        <template v-slot:activator="{ props: activatorProps }">
          <v-btn
            icon="mdi-cog"
            v-bind="activatorProps"
            variant="plain"
            size="small"
            class="settings-btn"
          />
        </template>

        <slot
          name="menu-content"
          :items="items"
          :prev-selected-items="props.selectedItems"
          :apply="applyFilters"
          :on-apply-finished="closeMenu"
          :cancel="cancel"
        >
          <Items
            :items="items"
            :selected-items="props.selectedItems"
            :search="search"
            :multiple="multiple"
            :limit="limit"
            @apply="applyFilters"
            @apply:finished="closeMenu"
            @cancel="cancel"
          >
            <template v-slot:append-toolbar>
              <slot name="append-toolbar" />
            </template>
            <template v-slot:icon="{ item }">
              <slot name="icon" :item="item" />
            </template>
            <template v-slot:no-items>
              <slot name="no-items" />
            </template>
            <template v-slot:title="{ item }">
              <slot name="title" :item="item" />
            </template>
          </items>
        </slot>
      </v-menu>
    </template>

    <slot :update-selected-items="emitInput">
      <items-selected
        :selected-items="selectedItems"
        :multiple="multiple"
        @update:select="emitInput"
      >
        <template v-slot:icon="{ item }">
          <slot name="icon" :item="item" />
        </template>

        <template v-slot:title="{ item }">
          <slot name="title" :item="item" />
        </template>
      </items-selected>
    </slot>
  </FilterToolbar>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from "vue";
import _ from "lodash";
import {
  Items,
  ItemsSelected,
  SelectedToolbarTitleItems
} from ".";
import FilterToolbar from "../Layout/FilterToolbar";

const props = defineProps({
  title: { type: String, required: true },
  bus: { type: Object, required: true },
  fetchItems: { type: Function, required: true },
  selectedItems: { type: Array, default: () => [] },
  multiple: { type: Boolean, default: true },
  search: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  panel: { type: Boolean, default: false },
  limit: { type: Number, default: null },
  apply: { type: Function, default: null }
});

const emit = defineEmits([
  "onMenuShow",
  "cancel",
  "select",
  "input",
  "clear"
]);

const items = ref([]);
const reloadItems = ref(true);
const menu = ref(false);
const allSelectedItems = ref([]);
const preventApply = ref(false);

function applyFilters(_selectedItems) {
  // Check if the given filter has a specific apply function to use and call it.
  // E.g. BaselineRunFilter
  if (props.apply) {
    props.apply(_selectedItems);
  } else {
    if (!filterIsChanged(_selectedItems)) return;
    emitInput(_selectedItems);
  }
}

watch(menu, async show => {
  if (show) {
    emit("onMenuShow");

    preventApply.value = false;

    if (reloadItems.value) {
      items.value = await props.fetchItems();
      reloadItems.value = false;
    }
  } else if (!preventApply.value) {
    applyFilters(allSelectedItems.value);
  }
});

onMounted(() => {
  props.bus.on("update", () => {
    reloadItems.value = true;
  });

  props.bus.on("select", predicate => {
    const item = items.value.find(predicate);
    if (item && !allSelectedItems.value.some(i => i.id === item.id)) {
      allSelectedItems.value.push(item);
    }
  });
});

onUnmounted(() => {
  props.bus.off("update", () => {});
  props.bus.off("select", () => {});
});

function closeMenu() {
  preventApply.value = true;
  menu.value = false;
}

/**
 * Returns true if the filter is changed, else false.
 */
function filterIsChanged(_selectedItems) {
  if (allSelectedItems.value.length !== _selectedItems.length) {
    return true;
  }

  const newSelection = _selectedItems.map(item => item.title).sort();
  const baseSelection = allSelectedItems.value.map(item => item.title).sort();

  if (_.xor(newSelection, baseSelection)) {
    return true;
  }

  return false;
}

function cancel() {
  preventApply.value = true;
  menu.value = false;
  emit("cancel");
}

function emitInput(items) {
  const itemsArray = !props.multiple ? [ items ] : items;
  allSelectedItems.value = itemsArray;
  emit("input", items);
}
</script>
