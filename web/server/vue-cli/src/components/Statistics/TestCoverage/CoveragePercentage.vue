<template>
  <div
    class="coverage-percentage d-flex align-center"
    :title="title"
  >
    <v-progress-linear
      v-if="percent !== null"
      :model-value="percent"
      :color="color"
      bg-color="grey"
      height="8"
      rounded
      class="coverage-bar mr-2"
      aria-hidden="true"
    />
    <span class="coverage-value">
      {{ formatPercentage(percent) }}
    </span>
  </div>
</template>

<script setup>
import { computed } from "vue";

import {
  coverageLevel,
  formatPercentage,
  percentage
} from "./coverage-tree";

const props = defineProps({
  hit: { type: Number, required: true },
  found: { type: Number, required: true },
  unit: { type: String, default: "lines" },
  // Describes a hit entity, e.g. "executed" lines or "taken" branches.
  verb: { type: String, default: "executed" }
});

const LEVEL_COLORS = {
  high: "success",
  medium: "warning",
  low: "error",
  none: "grey"
};

const percent = computed(() => percentage(props.hit, props.found));

const color = computed(() => LEVEL_COLORS[coverageLevel(percent.value)]);

const title = computed(() => {
  if (percent.value === null)
    return `No ${props.unit} to cover`;

  return `${props.hit} of ${props.found} ${props.unit} ${props.verb} ` +
    `(${formatPercentage(percent.value)})`;
});
</script>

<style lang="scss" scoped>
.coverage-percentage {
  min-width: 140px;

  .coverage-bar {
    max-width: 80px;
  }

  .coverage-value {
    min-width: 48px;
    text-align: right;
    font-weight: bold;
  }
}
</style>
