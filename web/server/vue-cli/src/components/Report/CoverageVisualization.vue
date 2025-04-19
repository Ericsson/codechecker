<template>
  <div>
    <div class="coverage-container">
      <div class="coverage-header">
        <div class="coverage-title">
          Test Coverage
        </div>
        <v-btn
          small
          icon
          @click="toggleCoverage"
        >
          <v-icon>mdi-chart-bar</v-icon>
        </v-btn>
      </div>
      <div class="coverage-stats">
        <div class="coverage-stat">
          <span class="stat-value">{{ coverageData.totalLines }}</span>
          <span class="stat-label">Total Lines</span>
        </div>
        <div class="coverage-stat">
          <span class="stat-value">{{ coverageData.coveredLines }}</span>
          <span class="stat-label">Covered Lines</span>
        </div>
        <div class="coverage-stat">
          <span class="stat-value">{{ coveragePercentage }}%</span>
          <span class="stat-label">Coverage</span>
        </div>
      </div>
      <div class="coverage-bar">
        <div 
          class="coverage-progress" 
          :style="{ width: coveragePercentage + '%' }"
        />
      </div>
    </div>

    <div class="code-viewer">
      <div class="code-header">
        {{ fileName }}
      </div>
      <div class="code-content">
        <div 
          v-for="(line, index) in codeLines" 
          :key="index"
          class="line"
          :class="getLineClass(index + 1)"
        >
          <span class="line-number">{{ index + 1 }}</span>
          <span class="line-content">{{ line }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "CoverageVisualization",
  props: {
    coverageData: {
      type: Object,
      required: true,
      default: () => ({
        totalLines: 0,
        coveredLines: 0,
        lineCoverage: {}
      })
    },
    fileName: {
      type: String,
      default: "test.cpp"
    },
    codeLines: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    coveragePercentage() {
      if (this.coverageData.totalLines === 0) {
        return 0;
      }
      return Math.round(
        (this.coverageData.coveredLines / this.coverageData.totalLines) * 100
      );
    }
  },
  methods: {
    toggleCoverage() {
      this.$emit("toggle-coverage");
    },
    getLineClass(lineNumber) {
      const coverage = this.coverageData.lineCoverage[lineNumber];
      if (coverage === 1) return "covered-line";
      if (coverage === 0) return "uncovered-line";
      if (coverage === 0.5) return "partial-line";
      return "";
    }
  }
};
</script>

<style scoped>
.coverage-container {
  padding: 16px;
  background-color: #f5f5f5;
  border-radius: 4px;
  margin-bottom: 16px;
}

.coverage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.coverage-title {
  font-weight: bold;
  font-size: 16px;
}

.coverage-stats {
  display: flex;
  gap: 16px;
}

.coverage-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.coverage-bar {
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 8px;
}

.coverage-progress {
  height: 100%;
  background-color: #4caf50;
  transition: width 0.3s ease;
}

.code-viewer {
  border: 1px solid #d8dbe0;
  border-radius: 4px;
  margin-top: 16px;
}

.code-header {
  background-color: #f7f7f7;
  padding: 8px 16px;
  border-bottom: 1px solid #d8dbe0;
  font-family: monospace;
}

.code-content {
  padding: 16px;
  font-family: monospace;
  white-space: pre;
  line-height: 1.5;
}

.line {
  display: flex;
  padding: 2px 0;
}

.line-number {
  width: 40px;
  color: #666;
  text-align: right;
  padding-right: 16px;
}

.line-content {
  flex: 1;
}

.covered-line {
  background-color: rgba(76, 175, 80, 0.1);
}

.uncovered-line {
  background-color: rgba(244, 67, 54, 0.1);
}

.partial-line {
  background-color: rgba(255, 152, 0, 0.1);
}
</style> 