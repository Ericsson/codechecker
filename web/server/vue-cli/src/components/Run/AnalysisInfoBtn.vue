<template>
  <v-btn
    class="show-analysis-info"
    title="Show analysis information"
    color="grey darken-1"
    small
    text
    icon
    @click="$emit('click')"
  >
    <v-icon>mdi-console</v-icon>
  </v-btn>
</template>

<script>
export default {
  name: "AnalysisInfoBtn",
};
</script>
