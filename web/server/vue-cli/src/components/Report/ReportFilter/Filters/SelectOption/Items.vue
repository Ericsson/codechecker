<template>
  <v-card
    elevation="4"
  >
    <slot name="prepend-toolbar" />

    <v-toolbar
      v-if="search"
      class="pa-2"
      density="compact"
      elevation="0"
      color="transparent"
    >
      <v-text-field
        ref="search"
        v-model="searchTxt"
        autofocus
        hide-details
        prepend-icon="mdi-magnify"
        :label="search.placeHolder"
        variant="underlined"
        @update:model-value="filter"
      />
    </v-toolbar>

    <slot name="append-toolbar" />

    <v-list
      class="pa-2 overflow-y-auto"
      density="compact"
      :max-height="300"
    >
      <v-list-item
        v-if="searchTxt && search.regexLabel"
        class="my-1 regex-label"
        :value="searchTxt"
        @click="selectedRgx = selectedRgx === searchTxt ? null : searchTxt"
      >
        <template v-slot:prepend>
          <v-checkbox
            :model-value="selectedRgx === searchTxt"
            color="#28a745"
            class="ma-1 mr-5"
            hide-details="auto"
          />
        </template>

        <v-list-item-title>
          {{ search.regexLabel }}: {{ searchTxt }}
        </v-list-item-title>
      </v-list-item>

      <template v-if="items.length">
        <v-list-item
          v-for="item in processedItems"
          :key="item.id"
          :value="item.id"
          class="my-1"
          :disabled="!multiple && localSelectedItems === item.id"
          @click="toggleSelection(item)"
        >
          <template v-slot:prepend>
            <v-checkbox
              :model-value="isSelected(item.id)"
              color="#28a745"
              class="ma-1"
              hide-details="auto"
            />
            <slot name="icon" :item="item" />
          </template>

          <slot name="title" :item="item">
            <v-list-item-title :title="item.title">
              {{ item.title }}
            </v-list-item-title>
          </slot>

          <template v-slot:append>
            <slot
              name="prepend-count"
              :item="item"
            />

            <v-chip
              v-if="item.count !== undefined"
              color="#878d96"
              variant="outlined"
              size="small"
            >
              {{ item.count }}
            </v-chip>
          </template>
        </v-list-item>
      </template>

      <template v-else>
        <slot name="no-items">
          <v-list-item>
            <template v-slot:prepend>
              <v-icon>mdi-help-rhombus-outline</v-icon>
            </template>
            <v-list-item-title>
              No items
            </v-list-item-title>
          </v-list-item>
        </slot>
      </template>
    </v-list>

    <div
      v-if="limit"
      class="text-center text-secondary"
    >
      <span v-if="limit === items.length">Only the first</span>
      <i>{{ items.length }}</i> item(s) shown.
    </div>

    <v-card-actions>
      <v-spacer />

      <v-btn
        variant="text"
        class="cancel-btn"
        color="grey"
        @click="$emit('cancel')"
      >
        <v-icon>
          mdi-close-circle-outline
        </v-icon>
        Cancel
      </v-btn>

      <v-btn
        variant="text"
        class="apply-btn"
        color="primary"
        @click="apply"
      >
        <v-icon>
          mdi-check-circle-outline
        </v-icon>
        Apply
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import _ from "lodash";
import { computed, onMounted, ref } from "vue";

const props = defineProps({
  items: { type: Array, required: true },
  format: { type: Function, default: null },
  limit: { type: Number, default: null },
  selectedItems: { type: Array, required: true },
  multiple: { type: Boolean, default: true },
  search: { type: Object, default: null },
});

const emit = defineEmits([
  "cancel",
  "select",
  "update:items",
  "apply",
  "apply:finished"
]);

const searchTxt = ref(null);

const processedItems = computed(() => {
  if (!props.format) {
    return props.items;
  };
  return props.items.map(i => props.format(i));
});

const localSelectedItems = ref([]);

const selectedRgx = computed({
  get: () => {
    return props.selectedItems.find(item => item.id === searchTxt.value)
      ? searchTxt.value
      : null;
  },
  set: value => {
    const selectedItems = [ ...props.selectedItems ];
    const idx = selectedItems.findIndex(item => item.id === searchTxt.value);
    
    if (!value && idx !== -1) {
      selectedItems.splice(idx, 1);
    } else if (value && idx === -1) {
      selectedItems.push({ id: value, title: value });
    }
    
    emit("select", selectedItems);
  }
});

const filter = _.debounce(async value => {
  const items = await props.search.filterItems(value);
  emit("update:items", items);
}, 500);

onMounted(() => {
  localSelectedItems.value = props.selectedItems || [];
});

// Emit the `apply` event with the selected items.
function apply() {
  emit("apply", localSelectedItems.value);
  emit("apply:finished");
}

// Check if given item is selected.
function isSelected(id) {
  const selected = props.multiple ?
    localSelectedItems.value.some(item => item.id === id) :
    localSelectedItems.value?.id === id;

  return selected;
}

// Handle clicking on any of the items in the list.
function toggleSelection(_item) {
  if (props.multiple) {
    // This component supports selecting multiple options.
    if (localSelectedItems.value.some(itm => itm.id === _item.id)) {
      localSelectedItems.value =
        localSelectedItems.value.filter(itm => itm.id !== _item.id);
    } else {
      localSelectedItems.value = [ ...localSelectedItems.value, _item ];
    }
  } else {
    // This component supports selecting only one option.
    localSelectedItems.value = _item;
  }
}
</script>

<style lang="scss">
.regex-label {
  background-color: rgb(var(--v-theme-primary));
  color: white;
}
</style>