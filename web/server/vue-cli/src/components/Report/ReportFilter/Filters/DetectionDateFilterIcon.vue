<template>
  <v-avatar
    v-if="value === DetectionDateFilterItems.TODAY"
    title="Today"
    color="var(--color-soft-red)"
    size="24"
    tile
  >
    <span class="text-white font-weight-bold">T</span>
  </v-avatar>

  <v-avatar
    v-else-if="value === DetectionDateFilterItems.YESTERDAY"
    title="Yesterday"
    color="var(--color-soft-blue)"
    size="24"
    tile
  >
    <span class="text-white font-weight-bold">Y</span>
  </v-avatar>

  <v-avatar
    v-else-if="value === DetectionDateFilterItems.LAST_7_DAYS"
    title="Last 7 days"
    color="var(--color-soft-green)"
    size="24"
    tile
  >
    <span class="text-white font-weight-bold">7</span>
  </v-avatar>

  <v-avatar
    v-else-if="value === DetectionDateFilterItems.THIS_MONTH"
    title="This month"
    color="var(--color-soft-purple)"
    size="24"
    tile
  >
    <span class="text-white font-weight-bold">M</span>
  </v-avatar>

  <v-avatar
    v-else-if="value === DetectionDateFilterItems.THIS_YEAR"
    title="This year"
    color="var(--color-cool-gray-dark)"
    size="24"
    tile
  >
    <span class="text-white font-weight-bold">Y</span>
  </v-avatar>
</template>

<script setup>
import DetectionDateFilterItems from "./DetectionDateFilterItems";

defineProps({
  value: { type: Number, required: true }
});
</script>