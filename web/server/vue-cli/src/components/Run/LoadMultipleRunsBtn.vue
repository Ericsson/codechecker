<template>
  <v-btn
    class="diff-runs-btn px-4"
    variant="tonal"
    color="primary"
    height="40"
    :to="{ name: 'reports',
           query: {
             ...defaultReportFilterValues,
             ...reportFilterQuery
           }
    }"
  >
    <v-icon left>
      mdi-vector-combine
    </v-icon>
    LOAD SELECTED RUNS ({{ selected.length }})
  </v-btn>
</template>

<script setup>

import { defaultReportFilterValues } from "@/components/Report/ReportFilter";

defineProps({
  selected: { type: Array, default: () => [] },
  reportFilterQuery: { type: Object, default: () => {} },
});

</script>
