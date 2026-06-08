<template>
  <span
    class="selected-items"
    :title="title"
  >
    <v-chip class="px-1" color="grey" label small outlined>
      {{ value.length }}
    </v-chip>
    <span v-if="selectedItems">- {{ selectedItems }}</span>
  </span>
</template>

<script>
export default {
  name: "SelectedToolbarTitleItems",
  props: {
    value: { type: Array, default: () => [] },
  },
  computed: {
    selectedItems() {
      return this.value
        ? this.value.map(i => i.title).join(", ")
        : "";
    },

    title() {
      return this.selectedItems
        ? `Selected: ${this.selectedItems}.`
        : "No filter items are selected.";
    }
  },
};
</script>