<template>
  <v-icon
    v-if="value === 'successful'"
    color="#587549"
  >
    mdi-check
  </v-icon>

  <v-icon
    v-else-if="value === 'failed'"
    color="#964739"
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
