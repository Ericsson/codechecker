<template>
  <v-btn
    id="clear-all-filter-btn"
    color="primary"
    variant="outlined"
    prepend-icon="mdi-delete"
    @click="clearAllFilters"
  >
    Clear All Filters
  </v-btn>
</template>

<script setup>
const emit = defineEmits([ "clear" ]);

function clearAllFilters() {
  emit("clear");
}
</script>
