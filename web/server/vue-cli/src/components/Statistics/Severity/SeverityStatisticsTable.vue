<template>
  <base-statistics-table
    class="severity-statistics"
    :headers="headers"
    :items="items"
    :loading="loading"
    :mobile-breakpoint="1000"
    :colspan="1"
    loading-text="Loading severity statistics..."
    item-key="severity"
    :sort-by="[{ key: 'severity', order: 'desc' }]"
    :necessary-total="true"
  />
</template>

<script setup>
import { BaseStatisticsTable } from "@/components/Statistics";

defineProps({
  items: { type: Array, required: true },
  loading: { type: Boolean, default: false }
});

const headers = [
  {
    title: "Severity",
    key: "severity",
    align: "center"
  },
  {
    title: "Unreviewed",
    key: "unreviewed.count",
    align: "center"
  },
  {
    title: "Confirmed bug",
    key: "confirmed.count",
    align: "center"
  },
  {
    title: "Outstanding reports",
    key: "outstanding.count",
    align: "center"
  },
  {
    title: "False positive",
    key: "falsePositive.count",
    align: "center"
  },
  {
    title: "Intentional",
    key: "intentional.count",
    align: "center"
  },
  {
    title: "Suppressed reports",
    key: "suppressed.count",
    align: "center"
  },
  {
    title: "All reports",
    key: "reports.count",
    align: "center"
  }
];
</script>

<style lang="scss">
@use "@/components/Statistics/style.scss" with (
  $class-name: ".severity-statistics",
  $unreviewed_col: 2,
  $colspan: 0
);
</style>
