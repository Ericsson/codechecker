<template>
  <base-statistics-table
    :headers="headers"
    :items="items"
    :loading="loading"
    :mobile-breakpoint="1000"
    loading-text="Loading guideline statistics..."
    no-data-text="No guideline statistics available"
    item-key="guidelineRule"
    sort-by="checkers.severity"
    sort-desc
    @enabled-click="enabledClick"
  />  
</template>

<script>
import { BaseStatisticsTable } from "@/components/Statistics";

export default {
  name: "GuidelineStatisticsTable",
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
          text: "Guideline Name",
          value: "guidelineName"
        },
        {
          text: "Rule Name",
          value: "guidelineRule"
        },
        {
          text: "Related Checker(s)",
          value: "checkers.name"
        },
        {
          text: "Checker Severity",
          value: "checkers.severity",
          align: "center"
        },
        {
          text: "Checker Status",
          value: "checkers.enabledInAllRuns",
          align: "center"
        },
        {
          text: "Closed Reports",
          value: "checkers.closed",
          align: "center"
        },
        {
          text: "Outstanding Reports",
          value: "checkers.outstanding",
          align: "center"
        },
      ]
    };
  },
  methods: {
    enabledClick(type, checker_name) {
      this.$emit("enabled-click", type, checker_name);
    }
  }
};
</script>

<style lang="scss" scoped>
$class-name: ".checker-statistics > ::v-deep .v-data-table__wrapper";
@import "@/components/Statistics/style.scss";
</style>