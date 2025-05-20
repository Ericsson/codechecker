<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="8">
        <coverage-visualization-test />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import CoverageVisualizationTest 
  from "@/components/Report/CoverageVisualizationTest.vue";

export default {
  name: "CoverageTest",
  components: {
    CoverageVisualizationTest
  }
};
</script> 