<template>
  <base-statistics-table
    :headers="tableHeaders"
    :items="itemsWithUuid"
    :loading="loading"
    :mobile-breakpoint="1000"
    :item-class="getRowClass"
    loading-text="Loading guideline statistics..."
    no-data-text="No guideline statistics available"
    item-key="uuid"
    sort-by="checkers.severity"
    sort-desc
    @enabled-click="enabledClick"
  />
</template>

<script>
import { BaseStatisticsTable } from "@/components/Statistics";
import { v4 as uuidv4 } from "uuid";

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
          text: "Title",
          value: "guidelineRuleTitle"
        },
        {
          text: "Level",
          value: "guidelineLevel"
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

  computed: {
    hasTitle() {
      return this.items.some(item => item.guidelineRuleTitle);
    },

    hasLevel() {
      return this.items.some(item => item.guidelineLevel);
    },

    tableHeaders() {
      if (!this.headers) return;

      return this.headers.filter(header => {
        if (header.value === "guidelineRuleTitle") {
          return this.hasTitle;
        } else if (header.value === "guidelineLevel") {
          return this.hasLevel;
        }

        return true;
      });
    },

    itemsWithUuid() {
      return this.items.map(item => ({
        ...item,
        uuid: item.uuid || uuidv4()
      }));
    }
  },

  methods: {
    enabledClick(type, checker_name) {
      this.$emit("enabled-click", type, checker_name);
    },

    getRowClass(item) {
      const hasOutstanding = item.checkers.some(
        checker => checker.outstanding > 0);
      return hasOutstanding ? "highlight-row" : "";
    }
  }
};
</script>

<style lang="scss">
$class-name: ".checker-statistics > ::v-deep .v-data-table__wrapper";
@import "@/components/Statistics/style.scss";
</style>