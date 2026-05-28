<template>
  <base-statistics-table
    class="analysis-statistics"
    :headers="headers"
    :items="items"
    :loading="loading"
    :mobile-breakpoint="1000"
    loading-text="Loading checker statistics..."
    item-key="checker"
    :sort-by="[{ key: 'severity', order: 'desc' }]"
    @enabled-click="enabledClick"
  />
</template>

<script setup>
import { BaseStatisticsTable } from "@/components/Statistics";

defineProps({
  items: { type: Array, required: true },
  loading: { type: Boolean, default: false }
});

const emit = defineEmits([ "enabled-click" ]);

const headers = [
  {
    title: "Checker Name",
    key: "checker"
  },
  {
    title: "Guideline",
    key: "guidelineRules"
  },
  {
    title: "Severity",
    key: "severity",
    align: "center"
  },
  {
    title: "Status",
    key: "enabledInAllRuns",
    align: "center"
  },
  {
    title: "Closed Reports",
    key: "closed",
    align: "center"
  },
  {
    title: "Outstanding Reports",
    key: "outstanding",
    align: "center"
  }
];

function enabledClick(_type, _checker_name) {
  emit("enabled-click", _type, _checker_name);
}
</script>

<style lang="scss" scoped>
$class-name: ".checker-statistics >  :deep(.v-data-table__wrapper)";
@use "@/components/Statistics/style.scss";
</style>
