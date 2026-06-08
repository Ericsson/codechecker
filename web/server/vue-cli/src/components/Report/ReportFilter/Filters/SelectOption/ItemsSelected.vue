<template>
  <v-list
    v-if="localSelectedItems.length"
    class="pa-0"
    density="compact"
  >
    <v-list-item
      v-for="item in localSelectedItems"
      :key="item.id"
      :value="item"
      class="selected-item pa-0 px-1 ma-0 mb-1"
      :disabled="!multiple"
      density="compact"
      @click="removeSelected(item)"
    >
      <template v-slot:prepend>
        <div class="ma-1 mr-2">
          <slot name="icon" :item="item" />
        </div>
      </template>

      <slot name="title" :item="item">
        <v-list-item-title :title="item.title">
          {{ item.title }}
        </v-list-item-title>
      </slot>

      <template v-slot:append>
        <v-chip
          class="report-count"
          color="#878d96"
          variant="outlined"
          size="small"
        >
          {{ item.count || item.count === 0 ? item.count : "N/A" }}
        </v-chip>
        <v-icon
          class="remove-btn font-weight-bold"
          color="error"
          icon="mdi-close"
        />
      </template>
    </v-list-item>
  </v-list>

  <v-list-item
    v-else
    density="compact"
  >
    <v-list-item-title>No filter</v-list-item-title>
  </v-list-item>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";

const props = defineProps({
  selectedItems: { type: Array, required: true },
  multiple: { type: Boolean, default: true }
});

const emit = defineEmits([ "update:select" ]);

const localSelectedItems = ref([]);

onMounted(() => {
  localSelectedItems.value = props.selectedItems;
});

watch(() => props.selectedItems, val => {
  localSelectedItems.value = Array.isArray(val) ? val : [ val ];
}, { deep: true });

function removeSelected(_item) {
  if (localSelectedItems.value.some(itm => itm.id === _item.id)) {
    localSelectedItems.value =
      localSelectedItems.value.filter(itm => itm.id !== _item.id);
  }

  emit("update:select", localSelectedItems.value);
}
</script>

<style lang="scss" scoped>
.v-list-item.v-list-item--density-compact {
  min-height: auto;
}

.selected-item {
  position: relative;

  &:before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgb(var(--v-theme-primary));
    border-radius: 4px;
    opacity: 0.1;
  }

  &:hover:before {
    background-color: rgb(var(--v-theme-error));
  }

  .remove-btn {
    display: none;
  }

  &:hover {
    .report-count {
      display: none;
    }

    .remove-btn {
      display: block;
    }
  }
}
</style>
