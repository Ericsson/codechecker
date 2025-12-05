<template>
  <v-container
    class="analysis-info-checker-rows-in-columns"
  >
    <Checker
      v-for="(checker, idx) in checkers"
      :key="idx"
      :name="checker[0]"
      :enabled="checker[1].enabled"
    />
  </v-container>
</template>

<script setup>
import Checker from "./Checker";

defineProps({
  checkers: { type: Array, required: true }
});
</script>

<style lang="scss" scoped>
.analysis-info .analysis-info-checker-rows-in-columns {
  columns: 32em auto;
}
</style>
