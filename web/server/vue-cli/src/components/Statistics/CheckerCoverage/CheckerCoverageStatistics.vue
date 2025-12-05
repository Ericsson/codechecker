<template>
  <v-container fluid>
    <statistics-dialog
      v-if="type"
      v-model="showRuns[type]"
      :checker-name="selectedCheckerName"
      :type="type"
      :run-data="runData"
    />
    <v-row>
      <v-col>
        <h3 class="title text-primary mb-2">
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
            The tab shows all enabled checkers in the selected runs.
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
          <checker-coverage-statistics-table
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
            variant="outlined"
          >
            There is no proper run for <strong>checker coverage </strong>
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
            The Checker coverage statistics is not available 
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
          <checker-coverage-statistics-table
            :items="[]"
            :loading="loading"
          />
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

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
  MAX_QUERY_SIZE,
  ReportFilter,
  RunFilter
} from "@cc/report-server-types";
import StatisticsDialog from "../StatisticsDialog";
import CheckerCoverageStatisticsTable from "./CheckerCoverageStatisticsTable";

const props = defineProps({
  bus: { type: Object, required: true },
  namespace: { type: String, required: true }
});

const emit = defineEmits([ "refresh-filter" ]);

const router = useRouter();
const route = useRoute();
const severity = useSeverity();
const csv = useToCSV();
const baseStats = useBaseStatistics(props, null);
const analysisInfo = useAnalysisInfo();

const checker_stat = ref({});
const loading = ref(false);
const noProperRun = ref(false);
const problematicRuns = ref([]);
const runs = ref(null);
const runData = ref([]);
const selectedCheckerName = ref(null);
const showRuns = ref({
  enabled: false,
  disabled: false,
  problematic: false
});
const statistics = ref([]);
const type = ref(null);

const actualRunNames = computed(function() {
  return runs.value.filter(_run => !problematicRuns.value.map(
    _problematicRun => _problematicRun.runId
  ).includes(_run.runId)).map(_run => _run.runName);
});

watch(checker_stat, function(_stat) {
  statistics.value = Object.keys(_stat).map(_checker_id => {
    return {
      checker: _stat[_checker_id].checkerName,
      severity: _stat[_checker_id].severity,
      guidelineRules: _stat[_checker_id].guidelineRules,
      enabledInAllRuns: _stat[_checker_id].disabled.length === 0
        ? 1
        : 0,
      enabledRunLength: _stat[_checker_id].enabled.length,
      disabledRunLength: _stat[_checker_id].disabled.length,
      closed: _stat[_checker_id].closed.toNumber(),
      outstanding: _stat[_checker_id].outstanding.toNumber(),
    };
  });
});

watch(function() { return baseStats.runIds.value; }, async function() {
  noProperRun.value = false;
});

baseStats.setupRefreshListener(fetchStatistics);

function downloadCSV() {
  const _data = [
    [
      "Checker Name", "guideline", "Severity", "Status",
      "Closed Reports", "Outstanding Reports",
    ],
    ...statistics.value.map(_stat => {
      return [
        _stat.checker,
        formattedGuidelines(_stat.guidelineRules),
        severity.severityFromCodeToString(_stat.severity),
        _stat.enabledInAllRuns
          ? "Enabled in all selected runs"
          : "Not enabled in all selected runs",
        _stat.closed,
        _stat.outstanding
      ];
    })
  ];

  csv.toCSV(_data, "codechecker_checker_coverage_statistics.csv");
}

async function getRunData() {
  const _limit = MAX_QUERY_SIZE;
  let _offset = 0;
  
  const _filter = new RunFilter({
    ids: baseStats.runIds.value
  });

  const _runCount = await new Promise(_resolve => {
    ccService.getClient().getRunCount(
      _filter, handleThriftError(_runCnt => {
        _resolve(_runCnt.toNumber());
      }));
  });

  const _runs = [];

  for ( _offset; _offset <= _runCount; _offset+=_limit ) {
    const _limitedRuns = await new Promise(_resolve => {
      ccService.getClient().getRunData(
        _filter, _limit, _offset, null, handleThriftError(_runDataList => {
          _resolve(_runDataList.map(_runData => ({
            runId: _runData.runId,
            runName: _runData.name,
            codeCheckerVersion: _runData.codeCheckerVersion
          })));
        }));
    });
    _runs.push(..._limitedRuns);
  }
   
  return _runs;
}

async function fetchStatistics() {
  loading.value = true;

  await fetchProblematicRuns();

  const _filter = new ReportFilter(baseStats.reportFilter.value);

  const _checker_stat = await new Promise(_resolve => {
    ccService.getClient().getCheckerStatusVerificationDetails(
      baseStats.runIds.value,
      _filter,
      handleThriftError(_res => {
        _resolve(_res);
      }));
  });

  if ( _checker_stat !== undefined ) {
    const _checkers = Object.values(_checker_stat).map(_stat => {
      return new Checker({
        analyzerName: _stat.analyzerName,
        checkerId: _stat.checkerName
      });
    });

    const _guidelineRules = await new Promise(_resolve => {
      ccService.getClient().getCheckerLabels(
        _checkers,
        handleThriftError(_labels => {
          _resolve(_labels.map(_label => {
            const _guidelines = _label.filter(
              _param => _param.startsWith("guideline")
            );
            return _guidelines.map(_g => {
              const _guideline = _g.split("guideline:")[1];
              const _guidelineLabels = _label.filter(
                _param => _param.startsWith(_guideline)
              );
              return {
                type: _guideline,
                rules: _guidelineLabels.map(_gl => {
                  return _gl.split(`${_guideline}:`)[1];
                })
              };
            });
          }));
        })
      );
    });

    Object.keys(_checker_stat).forEach(
      (_key, _index) => {
        _checker_stat[_key]["guidelineRules"] = _guidelineRules[_index]
        !== undefined
          ? _guidelineRules[_index]
          : null;
      });
  }
  
  checker_stat.value = _checker_stat;
  loading.value = false;
}

async function fetchProblematicRuns() {
  loading.value = true;

  const _runs = await getRunData();
  problematicRuns.value = (await Promise.all(
    _runs.map(async _runData => {
      var _analysisInfo = await analysisInfo.loadAnalysisInfo(
        _runData.runId, null, null);

      if (_analysisInfo.checkerInfoAvailability !=
      CheckerInfoAvailability.Available) {
        return {
          ..._runData,
          analysisInfo: _analysisInfo
        };
      } else {
        return null;
      }
    }))).filter(_element => _element !== null);
  
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
    const _checker_id = Object.keys(checker_stat.value).find(_id =>
      checker_stat.value[_id].checkerName === _checker_name
    );

    runData.value = checker_stat.value[_checker_id][_type].map(
      _run_id => runs.value.find(
        _runData => _runData.runId.toNumber() === _run_id.toNumber()
      )
    );
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

function formattedGuidelines(_guidelineRules) {
  return _guidelineRules.map(_guidelineRule => {
    const _rules = _guidelineRule.rules.join("; ");
    return `${_guidelineRule.type}: ${_rules}`;
  }).join("  ");
}
</script>
