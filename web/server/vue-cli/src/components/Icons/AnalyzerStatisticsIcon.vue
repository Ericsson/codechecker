<template>
  <v-icon
    v-if="value === 'successful'"
    class="analyzer-statistics-icon-successful"
  >
    mdi-check
  </v-icon>

  <v-icon
    v-else-if="value === 'failed'"
    class="analyzer-statistics-icon-failed"
  >
    mdi-close
  </v-icon>
</template>

<script>
export default {
  name: "AnalyzerStatisticsIcon",
  props: {
    value: { type: String, required: true }
  }
};
</script>
<style lang="scss">
.analyzer-statistics-icon-successful {
  color: #587548 !important;
}
.analyzer-statistics-icon-failed {
  color: #964739 !important;
}
</style>
