<template>
  <v-avatar
    v-if="value === DetectionDateFilterItems.TODAY"
    title="Today"
    color="#ee8985"
    size="24"
    tile
  >
    <span class="white--text font-weight-bold">T</span>
  </v-avatar>

  <v-avatar
    v-else-if="value === DetectionDateFilterItems.YESTERDAY"
    title="Yesterday"
    color="#007ea7"
    size="24"
    tile
  >
    <span class="white--text font-weight-bold">Y</span>
  </v-avatar>

  <v-avatar
    v-else-if="value === DetectionDateFilterItems.LAST_7_DAYS"
    title="Last 7 days"
    color="#54ae5f"
    size="24"
    tile
  >
    <span class="white--text font-weight-bold">7</span>
  </v-avatar>

  <v-avatar
    v-else-if="value === DetectionDateFilterItems.THIS_MONTH"
    title="This month"
    color="#8f44ad"
    size="24"
    tile
  >
    <span class="white--text font-weight-bold">M</span>
  </v-avatar>

  <v-avatar
    v-else-if="value === DetectionDateFilterItems.THIS_YEAR"
    title="This year"
    color="#2e3f51"
    size="24"
    tile
  >
    <span class="white--text font-weight-bold">Y</span>
  </v-avatar>
</template>

<script setup>
import DetectionDateFilterItems from "./DetectionDateFilterItems";

defineProps({
  value: { type: Number, required: true }
});
</script>