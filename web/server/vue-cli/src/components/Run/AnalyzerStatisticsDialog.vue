<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="600px"
    scrollable
    title="Analyzer statistics"
    :buttons="false"
  >
    <template v-slot:content>
      <v-expansion-panels
        v-model="activeExpansionPanels"
        multiple
        hover
      >
        <v-expansion-panel
          v-for="(stats, analyzer) in analyzerStatistics"
          :key="analyzer"
        >
          <v-expansion-panel-title
            class="pa-0 px-1 text-primary font-weight-bold"
          >
            {{ analyzer }}
          </v-expansion-panel-title>

          <v-expansion-panel-text class="pa-1">
            <v-container>
              <v-row>
                <v-icon class="mr-2">
                  mdi-alpha-v-circle-outline
                </v-icon>
                <b class="pr-1">Version:</b> {{ stats.version }}
              </v-row>
              <v-row>
                <analyzer-statistics-icon
                  value="successful"
                  class="mr-2"
                />
                <b class="pr-1">Number of successfully analyzed files:</b>
                <v-chip
                  color="success"
                  size="small"
                >
                  {{ stats.successful }}
                </v-chip>
              </v-row>
              <v-row>
                <analyzer-statistics-icon
                  value="failed"
                  class="mr-2"
                />
                <b class="pr-1">Number of files which failed to analyze:</b>
                <v-chip
                  color="error"
                  size="small"
                >
                  {{ stats.failed }}
                </v-chip>
              </v-row>
              <v-row v-if="stats.failed">
                <v-icon class="mr-2">
                  mdi-text-box-multiple-outline
                </v-icon>
                <b>Files which failed to analyze:</b>
                <v-container class="pl-8">
                  <v-row>
                    <ul>
                      <li
                        v-for="file in stats.failedFilePaths"
                        :key="file"
                      >
                        {{ file }}
                      </li>
                    </ul>
                  </v-row>
                </v-container>
              </v-row>
            </v-container>
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

      activeExpansionPanels.value = [ ...Array(
        Object.keys(stats).length).keys() ];
    }));
}
</script>
