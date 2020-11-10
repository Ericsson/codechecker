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
    sort-by="severity"
    sort-desc
  />
</template>

<script>
import { BaseStatisticsTable } from "@/components/Statistics";

export default {
  name: "SeverityStatisticsTable",
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
$class-name: ".severity-statistics > ::v-deep .v-data-table__wrapper";
$unreviewed_col: 2;
$colspan: 0;

@import "@/components/Statistics/style.scss";
</style>
