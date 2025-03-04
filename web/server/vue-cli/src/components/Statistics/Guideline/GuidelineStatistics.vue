<template>
  <v-container fluid>
    <statistics-dialog
      v-if="type"
      :value.sync="showRuns[type]"
      :checker-name="selectedCheckerName"
      :type="type"
      :run-data="runData"
    />
    <v-row>
      <v-col>
        <h3 class="title primary--text mb-2">
          <v-btn
            color="primary"
            outlined
            @click="downloadCSV"
          >
            Export CSV
          </v-btn>

          <v-btn
            icon
            title="Reload statistics"
            color="primary"
            @click="fetchStatistics"
          >
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
          <tooltip-help-icon
            color="primary"
            size="x-large"
          >
            The tab displays the checker statistics for all the rules of the
            selected guideline, which are associated with the specified runs.
            <br><br>
            Please, first select runs in the left "Run/Tag Filter" menu.
            If the filter is empty all runs are selected.
            Specifying a run tag is not applied.
            <br><br>
            Please, note that this feature is available only for runs analysed
            natively with <strong>CodeChecker 6.24</strong> and above.
          </tooltip-help-icon>
        </h3>

        <v-alert
          icon="mdi-information"
          class="mt-2"
        >
          In this statistics only the "Run / Tag Filter"
          and the "Unique reports" are effective.
        </v-alert>

        <div v-if="!problematicRuns.length">
          <v-row align="center">
            <v-col cols="6">
              <v-select
                v-model="selectedGuidelineIndexes"
                :items="guidelineOptions"
                item-text="name"
                label="Select guidelines"
                outlined
                multiple
                density="comfortable"
              >
                <template v-slot:selection="{ item }">
                  <div class="selection-item">
                    {{ item.name }}
                  </div>
                </template>
              </v-select>
            </v-col>
          </v-row>
          <guideline-statistics-table
            :items="statistics"
            :loading="loading"
            @enabled-click="showingRuns"
          />
        </div>
        <div v-else>
          <v-alert
            v-if="noProperRun"
            icon="mdi-alert"
            class="mt-2"
            color="deep-orange"
            outlined
          >
            There is no proper run for <strong>guideline</strong>
            statistics. Please create a new run first that analysed
            natively with <strong>6.24</strong>
            or above version of CodeChecker!
          </v-alert>
          <v-alert
            v-else
            icon="mdi-alert"
            class="mt-2"
            color="deep-orange"
            outlined
          >
            The guideline statistics is not available
            for
            <span
              style="cursor: pointer; text-decoration: underline;"
              @click="showingRuns('problematic', null)"
            >
              <strong>some of</strong>
            </span>
            the selected runs.
            <br>
            Please modify the run filter or click the
            <span
              style="cursor: pointer; text-decoration: underline;"
              @click="cleanRunList"
            >
              <strong>restrict selection</strong>
            </span>
            button to get relevant statistics.
            <br>
          </v-alert>
          <guideline-statistics-table
            :items="[]"
            :loading="loading"
          />
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import {
  ReviewStatusMixin,
  SeverityMixin,
  ToCSV
} from "@/mixins";
import { AnalysisInfoHandlingAPIMixin } from "@/mixins/api";
import { BaseStatistics } from "@/components/Statistics";
import GuidelineStatisticsTable from "./GuidelineStatisticsTable";
import StatisticsDialog from "../StatisticsDialog";
import {
  Checker,
  Guideline,
  MAX_QUERY_SIZE,
  ReportFilter,
  RunFilter
} from "@cc/report-server-types";
import { ccService, handleThriftError } from "@cc-api";
import {
  CheckerInfoAvailability
} from "@/mixins/api/analysis-info-handling.mixin";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";

export default {
  name: "GuidelineStatistics",
  components: {
    GuidelineStatisticsTable,
    StatisticsDialog,
    TooltipHelpIcon
  },
  mixins: [
    AnalysisInfoHandlingAPIMixin,
    BaseStatistics,
    ReviewStatusMixin,
    SeverityMixin,
    ToCSV
  ],

  data() {
    // If there were more guideline types,
    // we could list the existing guidelines here.
    const guidelineOptions = [
      {
        id: "sei-cert-c",
        name: "SEI CERT Coding Standard (C)",
        value: 0
      },
      {
        id: "sei-cert-cpp",
        name: "SEI CERT Coding Standard (C++)",
        value: 1
      },
      {
        id: "cwe-top-25-2024",
        name: "CWE Top 25 Most Dangerous Software Weaknesses 2024",
        value: 2
      }
    ];

    return {
      all_guideline_rules: {},
      guidelineOptions: guidelineOptions,
      checker_stat: {},
      guideline_stat: {},
      loading: false,
      noProperRun: false,
      problematicRuns: [],
      runs: null,
      runData: [],
      selectedCheckerName: null,
      selectedGuidelineIndexes: [ 0, 1, 2 ],
      showRuns: {
        enabled: false,
        disabled: false,
        problematic: false
      },
      statistics: [],
      type: null,
    };
  },

  computed: {
    actualRunNames() {
      return this.runs.filter(run => !this.problematicRuns.map(
        problematicRun => problematicRun.runId
      ).includes(run.runId)).map(run => run.runName);
    },

    selectedGuidelines() {
      return this.selectedGuidelineIndexes.map(idx => new Guideline({
        guidelineName: this.guidelineOptions[idx].id
      }));
    }
  },

  watch: {
    checker_stat(stat) {
      this.statistics = [];
      Object.keys(this.all_guideline_rules).forEach(
        guideline => {
          this.statistics.push(
            ...this.all_guideline_rules[guideline].map(rule => {
              const filtered_stat = Object.keys(stat).filter(
                checkerId => rule.checkers.map(c => c.checkerName).includes(
                  stat[checkerId].checkerName));
              return {
                guidelineName: guideline,
                guidelineRule: rule.ruleId,
                guidelineUrl: rule.url,
                guidelineRuleTitle: rule.title,
                checkers: filtered_stat.length
                  ? filtered_stat.map(checkerId => {
                    return {
                      name: stat[checkerId].checkerName,
                      severity: stat[checkerId].severity,
                      enabledInAllRuns: stat[checkerId].disabled.length === 0
                        ? 1
                        : 0,
                      enabledRunLength: stat[checkerId].enabled.length,
                      disabledRunLength: stat[checkerId].disabled.length,
                      closed: stat[checkerId].closed.toNumber(),
                      outstanding: stat[checkerId].outstanding.toNumber(),
                    };
                  })
                  : (rule.checkers.length ?
                    rule.checkers.map(checker => {
                      return {
                        name: checker.checkerName,
                        severity: this.severityFromStringToCode(
                          checker.severity),
                        enabledInAllRuns: 0,
                        enabledRunLength: 0,
                        disabledRunLength: this.runs.length,
                        closed: 0,
                        outstanding: 0,
                      };
                    })
                    : [])
              };
            })
          );
        });
    },

    async runIds() {
      this.noProperRun = false;
    },

    async selectedGuidelines() {
      await this.fetchStatistics();
    }
  },


  methods: {
    downloadCSV() {
      const values = [];
      this.statistics.forEach(stat => {
        stat.checkers.forEach(checker => {
          const value = [
            stat.guidelineName,
            stat.guidelineRule,
            stat.guidelineRuleTitle,
            checker.name,
            this.severityFromCodeToString(checker.severity),
            checker.enabledInAllRuns
              ? "Enabled in all selected runs"
              : "Not enabled in all selected runs",
            checker.closed,
            checker.outstanding
          ];

          values.push(value);
        });
      });

      const data = [
        [
          "Guideline Name", "Rule Name", "Rule Title", "Related Checker(s)",
          "Checker Severity", "Checker Status", "Closed Reports",
          "Outstanding Reports"
        ],
        ...values
      ];

      this.toCSV(data, "codechecker_guideline_statistics.csv");
    },

    async getAllGuidelineRules() {
      this.all_guideline_rules = await new Promise(resolve => {
        ccService.getClient().getGuidelineRules(
          this.selectedGuidelines,
          handleThriftError(async guidelines => {
            for (const [ guideline, rules ] of Object.entries(guidelines)) {
              const all_checkers = [];
              rules.forEach(rule => {
                rule.checkers.map(checker => {
                  const chk = new Checker({
                    analyzerName: null,
                    checkerId: checker
                  });

                  if (!all_checkers.some(
                    c => c.checkerId === chk.checkerId)) {
                    all_checkers.push(chk);
                  }
                });
              });

              const checkers_with_severity = await new Promise(resolve => {
                ccService.getClient().getCheckerLabels(
                  all_checkers, handleThriftError(labels => {
                    resolve(
                      labels.map((label, i) => {
                        const severityLabels = label.filter(param =>
                          param.startsWith("severity")
                        );
                        return severityLabels.length
                          ? {
                            checkerName: all_checkers[i].checkerId,
                            severity: severityLabels[0].split("severity:")[1]
                          }
                          : {
                            checkerName: all_checkers[i].checkerId,
                            severity: null
                          };
                      })
                    );
                  })
                );
              });

              guidelines[guideline] = rules.map(rule => {
                return {
                  ruleId: rule.ruleId,
                  title: rule.title,
                  url: rule.url,
                  checkers: checkers_with_severity.filter(
                    cws => rule.checkers.includes(cws.checkerName))
                };
              });
            }

            resolve(guidelines);
          })
        );
      });
    },

    async getRunData() {
      const limit = MAX_QUERY_SIZE;
      let offset = 0;

      const filter = new RunFilter({
        ids: this.runIds
      });

      const runCount = await new Promise(resolve => {
        ccService.getClient().getRunCount(
          filter, handleThriftError(runCnt => {
            resolve(runCnt.toNumber());
          }));
      });

      const runs = [];

      for ( offset; offset <= runCount; offset+=limit ) {
        const limitedRuns = await new Promise(resolve => {
          ccService.getClient().getRunData(
            filter, limit, offset, null, handleThriftError(runDataList => {
              resolve(runDataList.map(runData => ({
                runId: runData.runId,
                runName: runData.name,
                codeCheckerVersion: runData.codeCheckerVersion
              })));
            }));
        });
        runs.push(...limitedRuns);
      }

      return runs;
    },

    async fetchStatistics() {
      this.loading = true;

      await this.fetchProblematicRuns();

      await this.getAllGuidelineRules();

      const filter = new ReportFilter(this.reportFilter);

      const checker_stat = await new Promise(resolve => {
        ccService.getClient().getCheckerStatusVerificationDetails(
          this.runIds,
          filter,
          handleThriftError(res => {
            resolve(res);
          }));
      });

      this.checker_stat = checker_stat;
      this.loading = false;
    },

    async fetchProblematicRuns() {
      this.loading = true;

      const runs = await this.getRunData();
      this.problematicRuns = (await Promise.all(
        runs.map(async runData => {
          var analysisInfo = await this.loadAnalysisInfo(
            runData.runId, null, null);

          if (analysisInfo.checkerInfoAvailability !=
          CheckerInfoAvailability.Available) {
            return {
              ...runData,
              analysisInfo: analysisInfo
            };
          } else {
            return null;
          }
        }))).filter(element => element !== null);

      this.runs = runs;
      this.loading = false;
    },

    showingRuns(type, checker_name) {
      this.type = type;
      this.selectedCheckerName = checker_name;
      if ( type === "problematic" ) {
        this.runData = this.problematicRuns;
      }
      else {
        const checker_id = Object.keys(this.checker_stat).find(checker_id =>
          this.checker_stat[checker_id].checkerName === checker_name
        );

        if ( checker_id ) {
          this.runData = this.checker_stat[checker_id][type].map(
            run_id => this.runs.find(
              runData => runData.runId.toNumber() === run_id.toNumber()
            )
          );
        }
        else {
          this.runData = this.runs;
        }
      }

      this.showRuns[type] = true;
    },

    cleanRunList() {
      if ( this.actualRunNames.length ){
        this.$router.replace({
          query: {
            ...this.$route.query,
            "run": this.actualRunNames
          }
        }).then(() => {
          this.$emit("refresh-filter");
        }).catch(() => {});
      }
      else {
        this.noProperRun = true;
      }
    },

    formattedGuidelines(guidelineRules) {
      return guidelineRules.map(guidelineRule => {
        const rules = guidelineRule.rules.join("; ");
        return `${guidelineRule.type}: ${rules}`;
      }).join("  ");
    }
  }
};
</script>

<style scoped>
  .selection-item {
    display: block;
    width: 100%;
  }
</style>
