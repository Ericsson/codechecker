<template>
  <span
    class="analyzer-statistics"
    :title="'Analysis statistics: shows the number of successfully analyzed ' +
      'files and the number of files which failed to analyze.'"
  >
    <component
      :is="tag"
      v-for="(analyzer, idx) in Object.keys(value)"
      :key="analyzer"
      class="text-no-wrap"
    >
      {{ analyzer }}:
      <span
        v-if="value[analyzer].successful.toNumber() !== 0"
        title="Number of successfully analyzed files."
      >
        <analyzer-statistics-icon value="successful" />
        ({{ value[analyzer].successful }})
      </span>
      <span
        v-if="value[analyzer].failed.toNumber() !== 0"
        title="Number of files which failed to analyze."
      >
        <analyzer-statistics-icon value="failed" />
        ({{ value[analyzer].failed }})
      </span>

      <v-divider
        v-if="showDividers && idx !== size - 1"
        class="mx-2 d-inline"
        inset
        vertical
      />
    </component>
  </span>
</template>

<script setup>
import { AnalyzerStatisticsIcon } from "@/components/Icons";
import { computed } from "vue";

const props = defineProps({
  value: { type: Object, required: true },
  tag: { type: String, default: "span" },
  showDividers: { type: Boolean, default: true }
});

const size = computed(function() {
  return Object.keys(props.value).length;
});
</script>

<style lang="scss">
  .analyzer-statistics {
    cursor: pointer;

    &:hover {
      color: var(--v-primary-base);
    }
  }
</style>
