<template>
  <span
    class="selected-items"
    :title="title"
  >
    <v-chip
      class="px-1"
      color="grey"
      rounded
      size="small"
      variant="outlined"
    >
      {{ selectedCount }}
    </v-chip>
  </span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  value: { type: Array, default: () => [] },
});


const selectedCount = computed(() =>
  Array.isArray(props.value) ? props.value.length : 1
);

const selectedItems = computed(() =>
  props.value && 
  Array.isArray(props.value) ? props.value.map(i => i.title).join(", ") : ""
);

const title = computed(() => {
  return selectedItems.value 
    ? `Selected: ${selectedItems.value}.` 
    : "No filter items are selected.";
}
);
</script>