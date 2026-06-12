<template>
  <v-btn
    variant="outlined"
    color="primary"
    class="diff-runs-btn mr-2"
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
    LOAD SELECTED RUNS
  </v-btn>
</template>

<script setup>

import { defaultReportFilterValues } from "@/components/Report/ReportFilter";

defineProps({
  reportFilterQuery: { type: Object, default: () => {} },
});

</script>
