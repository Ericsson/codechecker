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
        />
        <div class="text-caption mt-1">
          {{ tile.hit }} / {{ tile.found }} {{ tile.unit }} executed
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { computed } from "vue";

import CoveragePercentage from "./CoveragePercentage";

const props = defineProps({
  // Summed coverage counts: linesFound, linesHit, functionsFound,
  // functionsHit.
  counts: { type: Object, required: true }
});

const tiles = computed(() => [
  {
    label: "Line coverage",
    icon: "mdi-format-list-numbered",
    unit: "lines",
    hit: props.counts.linesHit,
    found: props.counts.linesFound
  },
  {
    label: "Function coverage",
    icon: "mdi-function-variant",
    unit: "functions",
    hit: props.counts.functionsHit,
    found: props.counts.functionsFound
  }
]);
</script>

<style lang="scss" scoped>
.coverage-summary-tile {
  min-width: 240px;
}
</style>
