<template>
  <div class="test-container">
    <coverage-visualization
      :coverage-data="testCoverageData"
      @toggle="handleToggle"
    />
  </div>
</template>

<script>
import CoverageVisualization from "./CoverageVisualization.vue";

export default {
  name: "CoverageVisualizationTest",
  components: {
    CoverageVisualization
  },
  data() {
    return {
      testCoverageData: {
        totalLines: 100,
        coveredLines: 75,
        lineCoverage: {
          1: 1,   // covered
          2: 1,   // covered
          3: 0,   // uncovered
          4: 1,   // covered
          5: 0.5, // partially covered
          6: 1,   // covered
          7: 0,   // uncovered
          8: 1,   // covered
          9: 0,   // uncovered
          10: 1   // covered
        }
      }
    };
  },
  methods: {
    handleToggle(show) {
      console.log("Coverage visibility toggled:", show);
    }
  }
};
</script>

<style scoped>
.test-container {
  max-width: 600px;
  margin: 20px auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
</style> 