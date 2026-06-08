<template>
  <v-btn
    :to="{ name: 'statistics',
           query: {
             ...defaultStatisticsFilterValues,
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
import { defaultStatisticsFilterValues } from "@/components/Statistics";

defineProps({
  extraQueries: { type: Object, default: () => {} }
});
</script>
