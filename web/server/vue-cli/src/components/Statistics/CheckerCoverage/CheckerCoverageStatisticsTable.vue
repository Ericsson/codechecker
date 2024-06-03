<template>
  <base-statistics-table
    class="analysis-statistics"
    :headers="headers"
    :items="items"
    :loading="loading"
    :mobile-breakpoint="1000"
    loading-text="Loading checker statistics..."
    item-key="checker"
    sort-by="severity"
    sort-desc
    @enabled-click="enabledClick"
  />
</template>

<script>
import { BaseStatisticsTable } from "@/components/Statistics";

export default {
  name: "CheckerCoverageStatisticsTable",
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
          text: "Checker Name",
          value: "checker"
        },
        {
          text: "Guideline",
          value: "guidelineRules"
        },
        {
          text: "Severity",
          value: "severity",
          align: "center"
        },
        {
          text: "Status",
          value: "enabledInAllRuns",
          align: "center"
        },
        {
          text: "Closed Reports",
          value: "closed",
          align: "center"
        },
        {
          text: "Outstanding Reports",
          value: "outstanding",
          align: "center"
        }
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
