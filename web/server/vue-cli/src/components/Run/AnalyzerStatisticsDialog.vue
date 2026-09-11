<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="600px"
    scrollable
    title="Analyzer statistics"
    :buttons="false"
  >
    <template v-slot:content>
      <div
        v-if="analyzerStatistics"
        class="d-flex align-center ga-2 mb-4"
      >
        <v-chip
          variant="tonal"
          color="primary"
          prepend-icon="mdi-cog-outline"
        >
          {{ analyzerCount }}
          {{ analyzerCount === 1 ? "analyzer" : "analyzers" }}
        </v-chip>

        <v-divider
          v-if="totalSuccessful || totalFailed"
          class="mx-1 d-inline"
          inset
          vertical
        />

        <v-chip
          v-if="totalSuccessful"
          variant="tonal"
          color="success"
        >
          <analyzer-statistics-icon value="successful" class="mr-1" />
          {{ totalSuccessful }}
        </v-chip>

        <v-chip
          v-if="totalFailed"
          variant="tonal"
          color="error"
        >
          <analyzer-statistics-icon value="failed" class="mr-1" />
          {{ totalFailed }}
        </v-chip>
      </div>

      <v-expansion-panels
        v-model="activeExpansionPanels"
        multiple
        hover
        variant="accordion"
      >
        <v-expansion-panel
          v-for="(stats, analyzer) in analyzerStatistics"
          :key="analyzer"
        >
          <v-expansion-panel-title class="py-2">
            <div class="d-flex align-center w-100 ga-2 flex-wrap">
              <v-icon
                class="ml-2"
                :color="stats.failed > 0 ? 'error' : 'success'"
                size="18"
              >
                {{ stats.failed > 0 ? "mdi-alert-circle" : "mdi-check-circle" }}
              </v-icon>

              <span class="font-weight-bold text-primary">
                {{ analyzer }}
              </span>

              <span class="text-caption text-medium-emphasis">
                v{{ stats.version }}
              </span>

              <v-spacer />

              <v-chip
                size="small"
                variant="tonal"
                color="success"
              >
                <analyzer-statistics-icon value="successful" class="mr-1" />
                {{ stats.successful }}
              </v-chip>

              <v-chip
                v-if="stats.failed"
                size="small"
                variant="tonal"
                color="error"
                class="mr-2"
              >
                <analyzer-statistics-icon value="failed" class="mr-1" />
                {{ stats.failed }}
              </v-chip>
            </div>
          </v-expansion-panel-title>

          <v-expansion-panel-text v-if="stats.failed > 0">
            <div class="ml-2 text-caption text-medium-emphasis mb-1">
              <v-icon
                color="error"
                size="18"
              >
                mdi-close
              </v-icon>
              Files failed to analyze:
            </div>
            <v-list
              density="compact"
              class="failed-files-list"
            >
              <v-list-item
                v-for="file in stats.failedFilePaths"
                :key="file"
                prepend-icon="mdi-file-alert-outline"
                prepend-gap="8"
              >
                <span class="text-caption font-mono">{{ file }}</span>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
          <v-expansion-panel-text v-else>
            <div class="ml-2 text-caption text-medium-emphasis mb-1">
              <v-icon
                color="success"
                size="18"
              >
                mdi-check
              </v-icon>
              All files were analyzed successfully!
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { AnalyzerStatisticsIcon } from "@/components/Icons";
import { ccService, handleThriftError } from "@cc-api";
import { computed, onMounted, ref, watch } from "vue";
import ConfirmDialog from "@/components/ConfirmDialog";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  runId: { type: Object, default: () => null },
  runHistoryId: { type: Object, default: () => null }
});

const emit = defineEmits([ "update:modelValue" ]);

const analyzerStatistics = ref(null);
const activeExpansionPanels = ref([]);

const dialog = computed({
  get() {
    return props.modelValue;
  },
  set(val) {
    emit("update:modelValue", val);
  }
});

const analyzerCount = computed(function() {
  return analyzerStatistics.value
    ? Object.keys(analyzerStatistics.value).length
    : 0;
});

const totalSuccessful = computed(function() {
  if (!analyzerStatistics.value) return 0;
  return Object.values(analyzerStatistics.value)
    .reduce((sum, s) => sum + Number(s.successful), 0);
});

const totalFailed = computed(function() {
  if (!analyzerStatistics.value) return 0;
  return Object.values(analyzerStatistics.value)
    .reduce((sum, s) => sum + Number(s.failed), 0);
});

watch(() => props.runId, function() {
  getAnalysisStatistics();
});

watch(() => props.runHistoryId, function() {
  getAnalysisStatistics();
});

onMounted(function() {
  getAnalysisStatistics();
});

function getAnalysisStatistics() {
  if (!dialog.value && !props.runId && !props.runHistoryId) return;

  ccService.getClient().getAnalysisStatistics(props.runId,
    props.runHistoryId, handleThriftError(stats => {
      analyzerStatistics.value = stats;

      // Only auto-expand analyzers that have failures, so attention goes
      // straight to the ones that need it. Clean analyzers stay collapsed.
      activeExpansionPanels.value = Object.keys(stats)
        .map((analyzer, idx) => ({ analyzer, idx }))
        .filter(({ analyzer }) => Number(stats[analyzer].failed) > 0)
        .map(({ idx }) => idx);
    }));
}
</script>

<style lang="scss" scoped>
.failed-files-list {
  max-height: 200px;
  overflow-y: auto;
}

.font-mono {
  font-family: monospace;
}
</style>

