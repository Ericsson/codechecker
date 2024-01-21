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
            v-for="cmd in analysisInfo.cmds"
            :key="cmd"
            class="analysis-info mb-2"
            v-html="cmd"
          />
        </v-container>

        <div
          v-if="analysisInfo.checkerInfoAvailable ===
            CheckerInfoAvailability.Normal"
        >
          <v-container class="pa-0 pt-1">
            <v-expansion-panels
              multiple
              hover
            >
              <v-expansion-panel
                v-for="analyzer in analysisInfo.analyzers"
                :key="analyzer"
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
                        :num-good="analysisInfo.counts[analyzer]
                          [GroupMeta.AnalyzerTotal][CountMeta.Enabled]"
                        :num-bad="analysisInfo.counts[analyzer]
                          [GroupMeta.AnalyzerTotal][CountMeta.Disabled]"
                        :num-total="analysisInfo.counts[analyzer]
                          [GroupMeta.AnalyzerTotal][CountMeta.Total]"
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
                      analysisInfo.checkers[analyzer]"
                  >
                    <checker-group
                      v-if="group !== GroupMeta.NoGroup"
                      :key="group"
                      :group="group"
                      :checkers="checkers"
                      :counts="analysisInfo.counts[analyzer][group]"
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
            class="mt-2"
            color="deep-orange"
            outlined
          >
            <span
              v-if="analysisInfo.checkerInfoAvailable ===
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
              v-else-if="analysisInfo.checkerInfoAvailable ===
                CheckerInfoAvailability.VersionTooLow"
            >
              The list of checkers executed during the analysis is only
              available from CodeChecker version
              <span class="version font-weight-bold">6.24</span>.<br>
              The analysis was executed using an older,
              <span class="version">{{
                analysisInfo.codeCheckerVersion
              }}</span>
              client, and it was also <span class="font-italic">likely</span>
              stored when the server ran this older version.
            </span>
            <span
              v-else-if="analysisInfo.checkerInfoAvailable ===
                CheckerInfoAvailability.ReportIdToAnalysisInfoNotTrivialOverAPI"
            >
              The list of checkers executed during the analysis that produced
              this <span class="font-italic">Report</span> is not
              available!<br>
            </span>
          </v-alert>
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
import { ccService, handleThriftError } from "@cc-api";
import {
  AnalysisInfoFilter,
  RunFilter,
  RunHistoryFilter
} from "@cc/report-server-types";
import { VersionMixin } from "@/mixins";

const GroupMeta = Object.freeze({ NoGroup: "__N", AnalyzerTotal: "__S" });
const CountMeta = Object.freeze({ Enabled: 0, Disabled: 1, Total: 2 });
const CheckerInfoAvailability = Object.freeze({
  Normal: 0,
  Unloaded: 1,
  UnknownReason: 2,
  VersionTooLow: 3,
  ReportIdToAnalysisInfoNotTrivialOverAPI: 4
});

export default {
  name: "AnalysisInfoDialog",
  components: {
    CheckerGroup,
    CheckerRows,
    CountChips
  },
  mixins: [ VersionMixin ],
  props: {
    value: { type: Boolean, default: false },
    runId: { type: Object, default: () => null },
    runHistoryId: { type: Object, default: () => null },
    reportId: { type: Object, default: () => null },
  },

  data() {
    return {
      analysisInfo: {
        cmds: [],
        analyzers: [],
        checkerInfoAvailable: CheckerInfoAvailability.Unloaded,
        codeCheckerVersion: "0",
        checkers: {},
        checkerCounts: {},
      },
      enabledCheckerRgx: new RegExp("^(--enable|-e[= ]*)", "i"),
      disabledCheckerRgx: new RegExp("^(--disable|-d[= ]*)", "i")
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
    GroupMeta() {
      return GroupMeta;
    },
    CountMeta() {
      return CountMeta;
    },
    CheckerInfoAvailability() {
      return CheckerInfoAvailability;
    }
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

    getTopLevelCheckGroup(analyzerName, checkerName) {
      const clangTidyClangDiagnostic = checkerName.split("clang-diagnostic-");
      if (clangTidyClangDiagnostic.length > 1 &&
        clangTidyClangDiagnostic[0] === "")
      {
        // Unfortunately, this is historically special...
        return "clang-diagnostic";
      }

      const splitDot = checkerName.split(".");
      if (splitDot.length > 1) {
        return splitDot[0];
      }

      const splitHyphen = checkerName.split("-");
      if (splitHyphen.length > 1) {
        if (splitHyphen[0] === analyzerName) {
          // cppcheck-PointerSize -> <NoGroup>
          // gcc-fd-leak          -> "fd"
          return splitHyphen.length >= 3 ? splitHyphen[1] : GroupMeta.NoGroup;
        }
        // bugprone-easily-swappable-parameters -> "bugprone"
        return splitHyphen[0];
      }

      return GroupMeta.NoGroup;
    },

    reduceCheckerStatuses(accumulator, newInfo) {
      for (const [ analyzer, checkers ] of Object.entries(newInfo)) {
        if (!accumulator[analyzer]) {
          accumulator[analyzer] = {};
          accumulator[analyzer][GroupMeta.NoGroup] = {};
        }
        for (const [ checker, checkerInfo ] of Object.entries(checkers)) {
          const group = this.getTopLevelCheckGroup(analyzer, checker);
          if (!accumulator[analyzer][group]) {
            accumulator[analyzer][group] = {};
          }
          accumulator[analyzer][group][checker] =
            accumulator[analyzer][group][checker] || checkerInfo.enabled;
        }
      }

      return accumulator;
    },

    sortAndStoreCheckerInfo(checkerStatuses) {
      this.analysisInfo.analyzers = Object.keys(checkerStatuses).sort();
      this.analysisInfo.checkers =
        Object.fromEntries(Object.keys(checkerStatuses).map(
          analyzer => [ analyzer,
            Object.fromEntries(
              Object.keys(checkerStatuses[analyzer]).sort().map(
                group => [ group,
                  Object.keys(checkerStatuses[analyzer][group]).sort().map(
                    checker => [ checker,
                      checkerStatuses[analyzer][group][checker]
                    ])
                ])
            )
          ]));

      this.analysisInfo.counts =
        Object.fromEntries(Object.keys(checkerStatuses).map(
          analyzer => [ analyzer,
            Object.fromEntries(
              Object.keys(checkerStatuses[analyzer]).map(
                group => [ group,
                  [
                    // [0]: #[Enabled checkers]
                    Object.keys(checkerStatuses[analyzer][group])
                      .map(checker =>
                        checkerStatuses[analyzer][group][checker] ? 1 : 0)
                      .reduce((a, b) => a + b, 0),
                    // [1]: #[Disabled checkers] (Note: will be updated later)
                    -1,
                    // [2]: #[Total checkers]
                    Object.keys(checkerStatuses[analyzer][group]).length
                  ]
                ]))
          ]));
      const counts = this.analysisInfo.counts;
      Object.keys(counts).map(
        analyzer => Object.keys(counts[analyzer]).map(
          group => {
            counts[analyzer][group][CountMeta.Disabled] =
              counts[analyzer][group][CountMeta.Total] -
              counts[analyzer][group][CountMeta.Enabled];
          }));
      Object.keys(counts).map(
        analyzer => {
          const sum = Object.values(counts[analyzer])
            .reduce((as, bs) => [
              as[CountMeta.Enabled]  + bs[CountMeta.Enabled],
              as[CountMeta.Disabled] + bs[CountMeta.Disabled],
              as[CountMeta.Total]    + bs[CountMeta.Total],
            ]);
          counts[analyzer][GroupMeta.AnalyzerTotal] = sum;
        });
    },

    checkerStatusUnavailableDueToVersion(version) {
      const normalized = this.prettifyCCVersion(version);
      if (!normalized) return false;
      this.analysisInfo.codeCheckerVersion = normalized;

      if (this.isNewerOrEqualCCVersion(normalized, "6.24")) return false;
      this.analysisInfo.checkerInfoAvailable =
        CheckerInfoAvailability.VersionTooLow;
      return true;
    },

    decideWhyCheckerStatusesUnavailable() {
      if (!this.runId && !this.runHistoryId && !this.reportId) {
        return;
      }

      if (this.runId && !this.runHistoryId) {
        const filter = new RunFilter({
          ids: [ this.runId ]
        });
        ccService.getClient().getRunData(filter, null, null, null,
          handleThriftError(runDataList => {
            if (runDataList.length !== 1) return;
            this.checkerStatusUnavailableDueToVersion(
              runDataList[0].codeCheckerVersion);
          }));
      } else if (this.runId && this.runHistoryId) {
        const filter = new RunHistoryFilter({
          tagNames: [],
          tagIds: [ this.runHistoryId ]
        });
        ccService.getClient().getRunHistory([ this.runId ], 1, 0, filter,
          handleThriftError(runHistoryDataList => {
            if (runHistoryDataList.length !== 1) return;
            this.checkerStatusUnavailableDueToVersion(
              runHistoryDataList[0].codeCheckerVersion);
          }));
      } else if (this.reportId) {
        this.analysisInfo.checkerInfoAvailable = CheckerInfoAvailability.
          ReportIdToAnalysisInfoNotTrivialOverAPI;
      }

      if (this.analysisInfo.checkerInfoAvailable !==
        CheckerInfoAvailability.UnknownReason) {
        // It was decided that the version is the reason.
        return;
      }
    },

    getAnalysisInfo() {
      if (
        !this.dialog ||
        (!this.runId && !this.runHistoryId && !this.reportId)
      ) {
        return;
      }

      const analysisInfoFilter = new AnalysisInfoFilter({
        // Query a run's analysis info only if a run history ID is not explicit.
        runId: (!this.runHistoryId ? this.runId : null),
        runHistoryId: this.runHistoryId,
        reportId: this.reportId,
      });

      this.analysisInfo.checkerInfoAvailable =
        CheckerInfoAvailability.Unloaded;

      const limit = null;
      const offset = 0;
      ccService.getClient().getAnalysisInfo(analysisInfoFilter, limit,
        offset, handleThriftError(analysisInfo => {
          this.analysisInfo.cmds = analysisInfo.map(ai =>
            this.highlightOptions(ai.analyzerCommand));

          const checkerStatuses = analysisInfo.map(ai => ai.checkers).
            reduce(this.reduceCheckerStatuses, {});
          if (!Object.keys(checkerStatuses).length) {
            this.sortAndStoreCheckerInfo({}); // Zero the calculated data out.
            this.analysisInfo.checkerInfoAvailable =
              CheckerInfoAvailability.UnknownReason;

            this.decideWhyCheckerStatusesUnavailable();
          } else {
            this.sortAndStoreCheckerInfo(checkerStatuses);
            this.analysisInfo.checkerInfoAvailable =
              CheckerInfoAvailability.Normal;
          }
        }));
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .analysis-info {
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
