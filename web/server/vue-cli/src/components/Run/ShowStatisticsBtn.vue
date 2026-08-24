<template>
  <v-btn
    :to="{ name: 'statistics',
           query: {
             ...extraQueries
           }}"
    class="show-statistics"
    title="Show statistics"
    color="green"
    size="small"
    variant="text"
    icon="mdi-chart-line"
  />
</template>

<script setup>

defineProps({
  extraQueries: { type: Object, default: () => {} }
});
</script>
