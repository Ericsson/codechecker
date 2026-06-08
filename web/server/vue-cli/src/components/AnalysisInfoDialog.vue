<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="1000px"
    title="Analysis Info"
    :buttons="false"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-if="iconOnly"
        v-bind="activatorProps"
        id="show-analysis-info-btn"
        color="primary"
        :variant="iconVariant"
        :size="iconSize"
        icon="mdi-console"
      />
      <v-btn
        v-else
        v-bind="activatorProps"
        id="show-analysis-info-btn"
        color="primary"
        :variant="iconVariant"
        :size="iconSize"
        prepend-icon="mdi-console"
      >
        Analysis Info
      </v-btn>
    </template>
    <template v-slot:content>
      <div class="pa-0 pt-2">
        <!-- eslint-disable vue/no-v-html -->
        <div
          v-for="cmd in highlightedCmds"
          :key="cmd"
          class="analyze-command mb-2"
          v-html="cmd"
        />
      </div>
      <v-expansion-panels
        v-if="postProcessedAnalysisInfoReady &&
          analysisInfo.checkerInfoAvailability
          === CheckerInfoAvailability.Available"
        class="checker-statuses pa-0 pt-1"
        multiple
      >
        <v-expansion-panel
          v-for="analyzer in analysisInfo.analyzers"
          :key="analyzer"
          class="analyzer-checkers-panel"
          :data-analyzer-name="analyzer"
        >
          <v-expansion-panel-title
            class="pa-0 px-1"
          >
            <v-row
              no-gutters
              align="center"
            >
              <v-col
                cols="auto"
                class="pa-1 analyzer-name text-primary"
              >
                {{ analyzer }}
              </v-col>
              <v-col cols="auto">
                <count-chips
                  class="pl-2"
                  :num-good="analysisInfo.checkerGroupCounts[analyzer]
                    [GroupKeys.AnalyzerTotal]
                    [CountKeys.Enabled]"
                  :num-bad="analysisInfo.checkerGroupCounts[analyzer]
                    [GroupKeys.AnalyzerTotal]
                    [CountKeys.Disabled]"
                  :num-total="analysisInfo.checkerGroupCounts[analyzer]
                    [GroupKeys.AnalyzerTotal]
                    [CountKeys.Total]"
                  :good-text="'Number of checkers enabled (executed)'"
                  :bad-text="'Number of checkers disabled' +
                    '(not executed)'"
                  :total-text="'Number of checkers available'"
                  :simplify-showing-if-all="true"
                  :show-total="true"
                  :show-dividers="false"
                  :show-zero-chips="false"
                />
              </v-col>
            </v-row>
          </v-expansion-panel-title>

          <v-expansion-panel-text
            class="pa-1"
          >
            <v-expansion-panels
              multiple
              elevation="0"
            >
              <template
                v-for="(checkers, group) in
                  analysisInfo.checkersGroupedAndSorted[analyzer]"
              >
                <checker-group
                  v-if="group !== GroupKeys.NoGroup"
                  :key="`group-${group}`"
                  :group="group"
                  :checkers="checkers"
                  :counts="
                    analysisInfo.checkerGroupCounts[analyzer][group]"
                />
                <checker-rows
                  v-else
                  :key="`row-${group}`"
                  :checkers="checkers"
                />
              </template>
            </v-expansion-panels>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-alert
        v-else-if="postProcessedAnalysisInfoReady"
        icon="mdi-alert"
        class="checker-status-unavailable mt-2"
        color="deep-orange"
        variant="outlined"
      >
        <span
          v-if="analysisInfo.checkerInfoAvailability ===
            CheckerInfoAvailability.UnknownReason"
        >
          The list of checkers executed during the analysis is not
          available!<br>
          This is likely caused by storing a run from a report directory
          which was not created natively by
          <span class="top-level-command">CodeChecker analyze</span>.
          Using the
          <span
            class="top-level-command font-italic"
          >report-converter</span>
          on the results of third-party analysers can cause this, as it
          prevents CodeChecker from knowing about the analysis
          configuration.
        </span>
        <span
          v-else-if="analysisInfo.checkerInfoAvailability ===
            CheckerInfoAvailability.
              RunHistoryStoredWithOldVersionPre_v6_24"
        >
          The list of checkers executed during the analysis is only
          available from CodeChecker version
          <span class="version font-weight-bold">6.24</span>.<br>
          The analysis was executed using an older,
          <span class="version">{{
            analysisInfo.codeCheckerVersion
          }}</span>
          client, and it was also likely stored when the server ran this
          older version.
        </span>
        <span
          v-else-if="analysisInfo.checkerInfoAvailability ===
            CheckerInfoAvailability.
              ReportIdToAnalysisInfoIdQueryNontrivialOverAPI"
        >
          The list of checkers executed during the analysis that produced
          this <span class="font-italic">Report</span> is not
          available!<br>
        </span>
      </v-alert>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import ConfirmDialog from "@/components/ConfirmDialog";
import {
  CheckerGroup,
  CheckerRows
} from "@/components/AnalysisInfo";
import CountChips from "@/components/CountChips";

import {
  CheckerInfoAvailability,
  CountKeys,
  GroupKeys,
  decideNegativeCheckerStatusAvailability,
  useAnalysisInfo,
} from "@/composables/useAnalysisInfo";

const props = defineProps({
  runId: { type: Object, default: () => null },
  runHistoryId: { type: Object, default: () => null },
  reportId: { type: Object, default: () => null },
  iconOnly: { type: Boolean, default: false },
  iconSize: { type: String, default: "small" }
});
const postProcessedAnalysisInfoReady = ref(false);
const analysisInfo = ref(null);
const dialog = ref(false);
const highlightedCmds = ref([]);
const enabledCheckerRgx = ref(new RegExp("^(--enable|-e[= ]*)", "i"));
const disabledCheckerRgx = ref(new RegExp("^(--disable|-d[= ]*)", "i"));

const analysisInfoComp = useAnalysisInfo();

const iconVariant = computed(
  () => props.iconOnly ? "text" : "outlined"
);

watch(dialog, () => {
  if (dialog.value) {
    getAnalysisInfo();
  }
});

function highlightOptions(cmd) {
  return cmd.split(" ").map(param => {
    if (!param.startsWith("-")) {
      return param;
    }

    const classNames = [ "param" ];
    if (enabledCheckerRgx.value.test(param)) {
      classNames.push("enabled-checkers");
    } else if (disabledCheckerRgx.value.test(param)) {
      classNames.push("disabled-checkers");
    } else if (param.startsWith("--ctu")) {
      classNames.push("ctu");
    } else if (param.startsWith("--stats")) {
      classNames.push("statistics");
    }

    return `<span class="${classNames.join(" ")}">${param}</span>`;
  }).join(" ").replace(/(?:\r\n|\r|\n)/g, "<br>");
}

async function getAnalysisInfo() {
  if (
    (!props.runId && !props.runHistoryId && !props.reportId)
  ) {
    return;
  }
  postProcessedAnalysisInfoReady.value = false;
  analysisInfo.value = null;

  var _analysisInfo = await analysisInfoComp.loadAnalysisInfo(
    props.runId, props.runHistoryId, props.reportId);

  decideNegativeCheckerStatusAvailability(
    _analysisInfo, props.runId, props.runHistoryId, props.reportId);
  highlightedCmds.value = _analysisInfo.cmds.map(cmd =>
    highlightOptions(cmd));
  _analysisInfo.groupAndCountCheckers();

  analysisInfo.value = _analysisInfo;
  postProcessedAnalysisInfoReady.value = true;
}
</script>

<style lang="scss">
.analyze-command {
  border: 1px solid grey;
  padding: 4px;

  .param {
    background-color: rgba(0, 0, 0, 0.15);
    font-weight: bold;
    padding-left: 2px;
    padding-right: 2px;
  }

  .enabled-checkers {
    background-color: rgba(0, 142, 0, 0.15);
  }

  .disabled-checkers {
    background-color: rgba(142, 0, 0, 0.15);
  }

  .ctu, .statistics {
    background-color: rgba(0, 0, 142, 0.15);
  }

  .analyzer-name {
    font-size: 125%;
    font-weight: bold;
  }

  .version, .top-level-command {
    font-family: monospace;
    font-size: smaller;
  }
}
</style>
