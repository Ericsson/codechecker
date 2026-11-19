<template>
  <div class="d-flex flex-wrap ga-4">
    <v-card
      v-for="tile in tiles"
      :key="tile.label"
      variant="flat"
      class="coverage-summary-tile"
      border
    >
      <v-card-text class="pa-3">
        <div class="text-subtitle-2 mb-1">
          <v-icon size="small" class="mr-1">
            {{ tile.icon }}
          </v-icon>
          {{ tile.label }}
        </div>
        <coverage-percentage
          :hit="tile.hit"
          :found="tile.found"
          :unit="tile.unit"
          :verb="tile.verb"
        />
        <div class="text-caption mt-1">
          {{ tile.hit }} / {{ tile.found }} {{ tile.unit }} {{ tile.verb }}
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { computed } from "vue";

import CoveragePercentage from "./CoveragePercentage";

const props = defineProps({
  // Summed coverage counts, e.g. linesFound, linesHit.
  counts: { type: Object, required: true },
  // The shown metrics (elements of METRICS of coverage-tree.js).
  metrics: { type: Array, required: true }
});

const tiles = computed(() => props.metrics.map(metric => ({
  label: `${metric.title} coverage`,
  icon: metric.icon,
  unit: metric.unit,
  verb: metric.verb,
  hit: props.counts[metric.hit],
  found: props.counts[metric.found]
})));
</script>

<style lang="scss" scoped>
// The tiles share one row on wide screens and wrap on narrow ones.
.coverage-summary-tile {
  flex: 1 1 0;
  min-width: 170px;
}
</style>
