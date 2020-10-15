<template>
  <base-statistics-table
    class="checker-statistics"
    :headers="headers"
    :items="items"
    :loading="loading"
    :mobile-breakpoint="1000"
    loading-text="Loading checker statistics..."
    item-key="checker"
    sort-by="severity"
    sort-desc
  />
</template>

<script>
import { BaseStatisticsTable } from "@/components/Statistics";

export default {
  name: "CheckerStatisticsTable",
  components: {
    BaseStatisticsTable
  },
  props: {
    items: { type: Array, required: true },
    loading: { type: Boolean, default: false }
  },
  data() {
    return {
      headers: [
        {
          text: "Checker",
          value: "checker"
        },
        {
          text: "Severity",
          value: "severity",
          align: "center"
        },
        {
          text: "Unreviewed",
          value: "unreviewed.count",
          align: "center"
        },
        {
          text: "Confirmed bug",
          value: "confirmed.count",
          align: "center"
        },
        {
          text: "Outstanding reports",
          value: "outstanding.count",
          align: "center"
        },
        {
          text: "False positive",
          value: "falsePositive.count",
          align: "center"
        },
        {
          text: "Intentional",
          value: "intentional.count",
          align: "center"
        },
        {
          text: "Suppressed reports",
          value: "suppressed.count",
          align: "center"
        },
        {
          text: "All reports",
          value: "reports.count",
          align: "center"
        }
      ]
    };
  }
};
</script>

<style lang="scss" scoped>
$class-name: ".checker-statistics > ::v-deep .v-data-table__wrapper";
@import "@/components/Statistics/style.scss";
</style>
