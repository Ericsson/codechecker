<template>
  <v-container
    class="analyzer-statistics"
  >
    <div
      v-for="(stats, analyzer) in value"
      :key="analyzer"
      class="text-no-wrap"
    >
      {{ analyzer }}:
      <span v-if="stats.successful.toNumber() !== 0">
        <analyzer-statistics-icon value="successful" />
        ({{ stats.successful }})
      </span>
      <span v-if="stats.failed.toNumber() !== 0">
        <analyzer-statistics-icon value="failed" />
        ({{ stats.failed }})
      </span>
    </div>
  </v-container>
</template>

<script>
import { AnalyzerStatisticsIcon } from "@/components/Icons";

export default {
  name: "AnalyzerStatisticsBtn",
  components: {
    AnalyzerStatisticsIcon
  },
  props: {
    value: { type: Object, required: true }
  }
};
</script>

<style lang="scss">
  .analyzer-statistics {
    cursor: pointer;

    &:hover {
      color: var(--v-primary-base);
    }
  }
</style>
