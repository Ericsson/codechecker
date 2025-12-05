<template>
  <span class="pa-1 text-no-wrap" title="Number of reports">
    <v-icon :color="'#ec7672'">mdi-bug</v-icon>
    <b>{{ value }}</b>
  </span>
</template>

<script setup>
import { ref } from "vue";

defineProps({
  value: { type: Number, required: true }
});

const id = ref("report-count");

defineExpose({ id });
</script>
