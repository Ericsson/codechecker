<template>
  <v-dialog
    v-model="dialog"
    content-class="analysis-info"
    max-width="80%"
    scrollable
  >
    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Analysis information

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <v-container class="pa-0 pt-2">
          <!-- eslint-disable vue/no-v-html -->
          <div
            v-for="cmd in highlightedCmds"
            :key="cmd"
            class="analyze-command mb-2"
            v-html="cmd"
          />
        </v-container>

        <div
          v-if="postProcessedAnalysisInfoReady"
        >
          <div
            v-if="analysisInfo.checkerInfoAvailability ===
              CheckerInfoAvailability.Available"
          >
            <v-container class="checker-statuses pa-0 pt-1">
              <v-expansion-panels
                multiple
                hover
              >
                <v-expansion-panel
                  v-for="analyzer in analysisInfo.analyzers"
                  :key="analyzer"
                  class="analyzer-checkers-panel"
                  :data-analyzer-name="analyzer"
                >
                  <v-expansion-panel-header
                    class="pa-0 px-1"
                  >
                    <v-row
                      no-gutters
                      align="center"
                    >
                      <v-col
                        cols="auto"
                        class="pa-1 analyzer-name primary--text"
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
                  </v-expansion-panel-header>

                  <v-expansion-panel-content
                    class="pa-1"
                  >
                    <template
                      v-for="(checkers, group) in
                        analysisInfo.checkersGroupedAndSorted[analyzer]"
                    >
                      <checker-group
                        v-if="group !== GroupKeys.NoGroup"
                        :key="group"
                        :group="group"
                        :checkers="checkers"
                        :counts="
                          analysisInfo.checkerGroupCounts[analyzer][group]"
                      />
                      <checker-rows
                        v-else
                        :key="group"
                        :checkers="checkers"
                      />
                    </template>
                  </v-expansion-panel-content>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-container>
          </div>
          <div
            v-else
          >
            <v-alert
              icon="mdi-alert"
              class="checker-status-unavailable mt-2"
              color="deep-orange"
              outlined
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
          </div>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import {
  CheckerGroup,
  CheckerRows
} from "@/components/AnalysisInfo";
import CountChips from "@/components/CountChips";
import {
  default as AnalysisInfoHandlingAPIMixin,
  CheckerInfoAvailability,
  CountKeys,
  GroupKeys,
  decideNegativeCheckerStatusAvailability
} from "@/mixins/api/analysis-info-handling.mixin";

export default {
  name: "AnalysisInfoDialog",
  components: {
    CheckerGroup,
    CheckerRows,
    CountChips
  },
  mixins: [ AnalysisInfoHandlingAPIMixin ],
  props: {
    value: { type: Boolean, default: false },
    runId: { type: Object, default: () => null },
    runHistoryId: { type: Object, default: () => null },
    reportId: { type: Object, default: () => null },
  },

  data() {
    return {
      postProcessedAnalysisInfoReady: false,
      analysisInfo: null,
      highlightedCmds: [],
      enabledCheckerRgx: new RegExp("^(--enable|-e[= ]*)", "i"),
      disabledCheckerRgx: new RegExp("^(--disable|-d[= ]*)", "i"),
    };
  },

  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("update:value", val);
      }
    },
    CheckerInfoAvailability() { return CheckerInfoAvailability; },
    CountKeys() { return CountKeys; },
    GroupKeys() { return GroupKeys; },
  },

  watch: {
    runId() {
      this.getAnalysisInfo();
    },
    runHistoryId() {
      this.getAnalysisInfo();
    },
    reportId() {
      this.getAnalysisInfo();
    }
  },

  mounted() {
    this.getAnalysisInfo();
  },

  methods: {
    highlightOptions(cmd) {
      return cmd.split(" ").map(param => {
        if (!param.startsWith("-")) {
          return param;
        }

        const classNames = [ "param" ];
        if (this.enabledCheckerRgx.test(param)) {
          classNames.push("enabled-checkers");
        } else if (this.disabledCheckerRgx.test(param)) {
          classNames.push("disabled-checkers");
        } else if (param.startsWith("--ctu")) {
          classNames.push("ctu");
        } else if (param.startsWith("--stats")) {
          classNames.push("statistics");
        }

        return `<span class="${classNames.join(" ")}">${param}</span>`;
      }).join(" ").replace(/(?:\r\n|\r|\n)/g, "<br>");
    },

    async getAnalysisInfo() {
      if (
        !this.dialog ||
        (!this.runId && !this.runHistoryId && !this.reportId)
      ) {
        return;
      }
      this.postProcessedAnalysisInfoReady = false;
      this.analysisInfo = null;

      var analysisInfo = await this.loadAnalysisInfo(
        this.runId, this.runHistoryId, this.reportId);
      decideNegativeCheckerStatusAvailability(
        analysisInfo, this.runId, this.runHistoryId, this.reportId);
      this.highlightedCmds = analysisInfo.cmds.map(cmd =>
        this.highlightOptions(cmd));
      analysisInfo.groupAndCountCheckers();

      this.analysisInfo = analysisInfo;
      this.postProcessedAnalysisInfoReady = true;
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .analysis-info {
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
