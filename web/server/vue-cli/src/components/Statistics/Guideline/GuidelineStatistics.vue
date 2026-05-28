<template>
  <v-container
    fluid
  >
    <statistics-dialog
      v-if="type"
      v-model="showRuns[type]"
      :checker-name="selectedCheckerName"
      :type="type"
      :run-data="runData"
    />
    <v-row>
      <v-col>
        <h3
          class="title text-primary mb-2"
        >
          <v-btn
            color="primary"
            variant="outlined"
            @click="downloadCSV"
          >
            Export CSV
          </v-btn>

          <v-btn
            icon="mdi-refresh"
            title="Reload statistics"
            color="primary"
            variant="text"
            @click="fetchStatistics"
          />
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
      </v-col>
    </v-row>
    <v-row>
      <v-col>
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
                item-title="name"
                item-value="value"
                label="Select guidelines"
                variant="outlined"
                multiple
                density="comfortable"
              >
                <template v-slot:selection="{ item }">
                  <div class="selection-item">
                    {{ item.raw.name }}
                  </div>
                </template>
              </v-select>
            </v-col>
            <v-col cols="6">
              <v-checkbox
                v-model="hideNotOutstanding"
                label="Hide compliant rules"
                density="comfortable"
              />
            </v-col>
          </v-row>
          <guideline-statistics-table
            :items="filteredStatistics"
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
            variant="outlined"
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
            variant="outlined"
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

<script setup>
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import {
  CheckerInfoAvailability,
  useAnalysisInfo
} from "@/composables/useAnalysisInfo";
import { useBaseStatistics } from "@/composables/useBaseStatistics";
import { useSeverity } from "@/composables/useSeverity";
import { useToCSV } from "@/composables/useToCSV";
import { ccService, handleThriftError } from "@cc-api";
import {
  Checker,
  Guideline,
  MAX_QUERY_SIZE,
  ReportFilter,
  RunFilter
} from "@cc/report-server-types";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import StatisticsDialog from "../StatisticsDialog";
import GuidelineStatisticsTable from "./GuidelineStatisticsTable";

const emit = defineEmits([ "refresh-filter" ]);
const router = useRouter();
const route = useRoute();
const severity = useSeverity();
const toCSV = useToCSV();
const baseStatistics = useBaseStatistics();
const analysisInfoComp = useAnalysisInfo();

const guidelineOptions = ref([
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
  },
  {
    id: "owasp-top-10-2021",
    name: "OWASP Top 10 Web Application Security Risks 2021",
    value: 3
  },
  {
    id: "memory-safety",
    name: "Memory-safety related CWEs",
    value: 4
  }
]);
const all_guideline_rules = ref({});
const checker_stats = ref({});
const loading = ref(false);
const noProperRun = ref(false);
const problematicRuns = ref([]);
const runs = ref(null);
const runData = ref([]);
const selectedCheckerName = ref(null);
const selectedGuidelineIndexes = ref([ 0, 1, 2, 3, 4 ]);
const showRuns = ref({
  enabled: false,
  disabled: false,
  problematic: false
});
const statistics = ref([]);
const type = ref(null);
const hideNotOutstanding = ref(false);

const actualRunNames = computed(() => {
  return runs.value.filter(run => !problematicRuns.value.map(
    problematicRun => problematicRun.runId
  ).includes(run.runId)).map(run => run.runName);
});

const selectedGuidelines = computed(() => selectedGuidelineIndexes.value.map(
  idx => new Guideline({ guidelineName: guidelineOptions.value[idx].id })
));

const filteredStatistics = computed(() => {
  if (hideNotOutstanding.value) {
    return statistics.value.filter(stat =>
      stat.checkers.some(checker => checker.outstanding > 0)
    );
  }
  return statistics.value;
});

watch(() => baseStatistics.runIds, async () => {
  noProperRun.value = false;
});

watch(selectedGuidelines, async () => {
  await fetchStatistics();
});

onMounted(() => {
  fetchStatistics();
});

function checker_stat(stat) {
  statistics.value = [];
  Object.keys(all_guideline_rules.value).forEach(
    guideline => {
      statistics.value.push(
        ...all_guideline_rules.value[guideline].map(rule => {
          const filtered_stat = Object.keys(stat).filter(
            checkerId => rule.checkers.map(c => c.checkerName).includes(
              stat[checkerId].checkerName));
          return {
            guidelineName: guideline,
            guidelineRule: rule.ruleId,
            guidelineUrl: rule.url,
            guidelineRuleTitle: rule.title,
            guidelineLevel: rule.level,
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
                    severity: severity.severityFromStringToCode(
                      checker.severity),
                    enabledInAllRuns: 0,
                    enabledRunLength: 0,
                    disabledRunLength: runs.value.length,
                    closed: 0,
                    outstanding: 0,
                  };
                })
                : [])
          };
        })
      );
    });
}

function downloadCSV() {
  const _values = [];
  statistics.value.forEach(stat => {
    stat.checkers.forEach(checker => {
      const _value = [
        stat.guidelineName,
        stat.guidelineRule,
        stat.guidelineRuleTitle,
        checker.name,
        severity.severityFromCodeToString(checker.severity),
        checker.enabledInAllRuns
          ? "Enabled in all selected runs"
          : "Not enabled in all selected runs",
        checker.closed,
        checker.outstanding
      ];

      _values.push(_value);
    });
  });

  const _data = [
    [
      "Guideline Name", "Rule Name", "Rule Title", "Related Checker(s)",
      "Checker Severity", "Checker Status", "Closed Reports",
      "Outstanding Reports"
    ],
    ..._values
  ];

  toCSV.toCSV(_data, "codechecker_guideline_statistics.csv");
}

async function getAllGuidelineRules() {
  all_guideline_rules.value = await new Promise(resolve => {
    ccService.getClient().getGuidelineRules(
      selectedGuidelines.value,
      handleThriftError(async guidelines => {
        for (const [ guideline, rules ] of Object.entries(guidelines)) {
          const _all_checkers = [];
          rules.forEach(rule => {
            rule.checkers.map(checker => {
              const chk = new Checker({
                analyzerName: null,
                checkerId: checker
              });

              if (!_all_checkers.some(
                c => c.checkerId === chk.checkerId)) {
                _all_checkers.push(chk);
              }
            });
          });

          const _checkers_with_severity = await new Promise(resolve => {
            ccService.getClient().getCheckerLabels(
              _all_checkers, handleThriftError(labels => {
                resolve(
                  labels.map((label, i) => {
                    const severityLabels = label.filter(param =>
                      param.startsWith("severity")
                    );
                    return severityLabels.length
                      ? {
                        checkerName: _all_checkers[i].checkerId,
                        severity: severityLabels[0].split("severity:")[1]
                      }
                      : {
                        checkerName: _all_checkers[i].checkerId,
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
              checkers: _checkers_with_severity.filter(
                cws => rule.checkers.includes(cws.checkerName)),
              level: rule.level
            };
          });
        }

        resolve(guidelines);
      })
    );
  });
}

async function getRunData() {
  const _filter = new RunFilter({
    ids: baseStatistics.runIds
  });

  const _runCount = await new Promise(resolve => {
    ccService.getClient().getRunCount(
      _filter,
      handleThriftError(runCnt => {
        resolve(runCnt.toNumber());
      })
    );
  });

  const _runs = [];
  const _limit = MAX_QUERY_SIZE;
  for (let _offset = 0; _offset <= _runCount; _offset+=_limit) {
    const _limitedRuns = await new Promise(resolve => {
      ccService.getClient().getRunData(
        _filter,
        _limit,
        _offset,
        null,
        handleThriftError(runDataList => {
          resolve(
            runDataList.map(runData => ({
              runId: runData.runId,
              runName: runData.name,
              codeCheckerVersion: runData.codeCheckerVersion
            }))
          );
        })
      );
    });
    _runs.push(..._limitedRuns);
  }

  return _runs;
}

async function fetchStatistics() {
  loading.value = true;

  await fetchProblematicRuns();

  await getAllGuidelineRules();

  const filter = new ReportFilter(baseStatistics.reportFilter);

  const checker_stat_result = await new Promise(resolve => {
    ccService.getClient().getCheckerStatusVerificationDetails(
      baseStatistics.runIds,
      filter,
      handleThriftError(res => {
        resolve(res);
      }));
  });

  checker_stats.value = checker_stat_result;
  checker_stat(checker_stat_result);
  loading.value = false;
}

async function fetchProblematicRuns() {
  loading.value = true;

  const _runs = await getRunData();
  problematicRuns.value = (await Promise.all(
    _runs.map(async runData => {
      var _analysisInfo = await analysisInfoComp.loadAnalysisInfo(
        runData.runId, null, null);

      if (_analysisInfo.checkerInfoAvailability !=
      CheckerInfoAvailability.Available) {
        return {
          ...runData,
          analysisInfo: _analysisInfo
        };
      } else {
        return null;
      }
    }))).filter(element => element !== null);

  runs.value = _runs;
  loading.value = false;
}

function showingRuns(_type, _checker_name) {
  type.value = _type;
  selectedCheckerName.value = _checker_name;
  if ( _type === "problematic" ) {
    runData.value = problematicRuns.value;
  }
  else {
    const _checker_id = Object.keys(checker_stats.value).find(_checker_id =>
      checker_stats.value[_checker_id].checkerName === _checker_name
    );

    if (_checker_id) {
      runData.value = checker_stats.value[_checker_id][_type].map(
        run_id => runs.value.find(
          runData => runData.runId.toNumber() === run_id.toNumber()
        )
      );
    }
    else {
      runData.value = runs.value;
    }
  }

  showRuns.value[_type] = true;
}

function cleanRunList() {
  if ( actualRunNames.value.length ){
    router.replace({
      query: {
        ...route.query,
        "run": actualRunNames.value
      }
    }).then(() => {
      emit("refresh-filter");
    }).catch(() => {});
  }
  else {
    noProperRun.value = true;
  }
}
</script>

<style>
  .selection-item {
    display: block;
    width: 100%;
  }
</style>
