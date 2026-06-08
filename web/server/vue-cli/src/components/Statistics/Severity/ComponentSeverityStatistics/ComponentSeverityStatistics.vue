<template>
  <v-row justify="center">
    <v-col cols="12">
      <div class="text-left">
        <div class="text-h6 mb-4">
          Component severity statistics
          <tooltip-help-icon>
            This table shows component statistics per severity
            levels.
            <br><br>
            Each row can be expanded which will show a checker statistics
            for the actual component.
            <br><br>
            The following filters don't affect these values:
            <ul>
              <li><b>Severity</b> filter.</li>
              <li><b>Source component</b> filter.</li>
            </ul>
          </tooltip-help-icon>
        </div>
        <div class="d-flex justify-center">
          <component-severity-statistics-table
            :items="statistics"
            :loading="loading"
            :filters="statisticsFilters"
            :total-columns="totalColumns"
          >
            <template
              v-for="item in severityValues"
              v-slot:[getHeaderSlotName(item)]="{ column }"
              :key="item[0]"
            >
              <span>
                <severity-icon :status="item[1]" :size="16" />
                {{ column.title }}
              </span>
            </template>

            <template
              v-for="i in severityValues"
              v-slot:[getItemSlotName(i)]="{ item }"
              :key="i[0]"
            >
              <span>
                <router-link
                  v-if="item[i[0]].count"
                  :to="{ name: 'reports', query: {
                    ...router.currentRoute.value.query,
                    ...(item.$queryParams || {}),
                    'source-component': item.component,
                    'severity': severity.severityFromCodeToString(i[1])
                  }}"
                >
                  {{ item[i[0]].count }}
                </router-link>

                <report-diff-count
                  :num-of-new-reports="item[i[0]].new"
                  :num-of-resolved-reports="item[i[0]].resolved"
                  :extra-query-params="{
                    'source-component': item.component,
                    'severity': severity.severityFromCodeToString(i[1])
                  }"
                />
              </span>
            </template>

            <template v-slot:header.reports.count="{ column }">
              <detection-status-icon
                :status="DetectionStatus.UNRESOLVED"
                :size="16"
                left
              />
              {{ column.title }}
            </template>
          </component-severity-statistics-table>
        </div>
      </div>
    </v-col>
  </v-row>
  <v-row justify="center">
    <v-col cols="12">
      <div class="text-left">
        <div class="text-h6 mb-4">
          Report severities
          <tooltip-help-icon>
            This pie chart shows the checker severity distribution in the
            product.
            <br><br>
            The following filters don't affect these values:
            <ul>
              <li><b>Severity</b> filter.</li>
              <li><b>Source component</b> filter.</li>
            </ul>
          </tooltip-help-icon>
        </div>
        <div class="d-flex justify-center">
          <div style="width: 400px; height: 400px; position: relative;">
            <v-overlay
              :value="loading"
              :absolute="true"
              :opacity="0.2"
            >
              <v-progress-circular
                indeterminate
                size="64"
              />
            </v-overlay>
            <component-severity-statistics-chart
              :loading="loading"
              :statistics="statistics"
            />
          </div>
        </div>
      </div>
    </v-col>
  </v-row>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

import { DetectionStatusIcon, SeverityIcon } from "@/components/Icons";
import {
  ReportDiffCount,
  getComponents,
  initDiffField
} from "@/components/Statistics";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { useBaseStatistics } from "@/composables/useBaseStatistics";
import { useSeverity } from "@/composables/useSeverity";
import { ccService, handleThriftError } from "@cc-api";
import {
  CompareData,
  DetectionStatus,
  DiffType,
  ReportFilter,
  Severity
} from "@cc/report-server-types";

import ComponentSeverityStatisticsChart
  from "./ComponentSeverityStatisticsChart";
import ComponentSeverityStatisticsTable
  from "./ComponentSeverityStatisticsTable";

const props = defineProps({
  bus: { type: Object, required: true },
  namespace: { type: String, required: true }
});

const router = useRouter();
const severity = useSeverity();
const baseStats = useBaseStatistics(props, null);

const loading = ref(false);
const statistics = ref([]);
const components = ref([]);
const statisticsFilters = ref({});
const fieldsToUpdate = [ "critical", "high", "medium", "low", "style",
  "unspecified", "reports" ];
const totalColumns = fieldsToUpdate;

const severityValues = computed(function() {
  return [
    [ "critical", Severity.CRITICAL ],
    [ "high", Severity.HIGH ],
    [ "medium", Severity.MEDIUM ],
    [ "low", Severity.LOW ],
    [ "style", Severity.STYLE ],
    [ "unspecified", Severity.UNSPECIFIED ],
  ];
});

baseStats.setupRefreshListener(fetchStatistics);

function getHeaderSlotName(item) {
  return `header.${item[0]}.count`;
}

function getItemSlotName(i) {
  return `item.${i[0]}.count`;
}

function getComponentStatistics(component, runIds, reportFilter, cmpData) {
  const _filter = new ReportFilter(reportFilter);
  _filter["severity"] = null;
  _filter["componentNames"] = [ component.name ];

  return new Promise(_resolve =>
    ccService.getClient().getSeverityCounts(runIds, _filter, cmpData,
      handleThriftError(_res => _resolve(_res))));
}

function initStatistics(components) {
  statistics.value = components.map(_component => ({
    component   : _component.name,
    value       : _component.value || _component.description,
    reports     : initDiffField(undefined),
    critical    : initDiffField(undefined),
    high        : initDiffField(undefined),
    medium      : initDiffField(undefined),
    low         : initDiffField(undefined),
    style       : initDiffField(undefined),
    unspecified : initDiffField(undefined)
  }));
}

async function getStatistics(component, runIds, reportFilter, cmpData) {
  const _res = await getComponentStatistics(component, runIds,
    reportFilter, cmpData);

  const _reports = Object.keys(_res).reduce((_acc, _curr) => {
    _acc += _res[_curr].toNumber();
    return _acc;
  }, 0);

  return {
    component   : component.name,
    value       : component.value || component.description,
    reports     : initDiffField(_reports),
    critical    : initDiffField(_res[Severity.CRITICAL]),
    high        : initDiffField(_res[Severity.HIGH]),
    medium      : initDiffField(_res[Severity.MEDIUM]),
    low         : initDiffField(_res[Severity.LOW]),
    style       : initDiffField(_res[Severity.STYLE]),
    unspecified : initDiffField(_res[Severity.UNSPECIFIED])
  };
}

function updateCalculatedFields(oldValues, newValues, type) {
  if (oldValues["outstanding"] !== undefined) {
    oldValues["outstanding"][type] =
      newValues["unreviewed"].count + newValues["confirmed"].count;
  }

  if (oldValues["suppressed"] !== undefined) {
    oldValues["suppressed"][type] =
      newValues["falsePositive"].count + newValues["intentional"].count;
  }
}

async function fetchDifference() {
  if (!baseStats.cmpData.value) return;

  return Promise.all(components.value.map(_component => {
    const _q1 = getNewReports(_component).then(_newReports => {
      const _row = statistics.value.find(_s =>
        _s.component === _component.name);

      if (_row) {
        fieldsToUpdate.forEach(_f => _row[_f].new = _newReports[_f].count);
        updateCalculatedFields(_row, _newReports, "new");
      }
    });

    const _q2 = getResolvedReports(_component).then(_resolvedReports => {
      const _row = statistics.value.find(_s =>
        _s.component === _component.name);

      if (_row) {
        fieldsToUpdate.forEach(_f =>
          _row[_f].resolved = _resolvedReports[_f].count);
        updateCalculatedFields(_row, _resolvedReports, "resolved");
      }
    });

    return Promise.all([ _q1, _q2 ]);
  }));
}

function getNewReports(component) {
  const _runIds = baseStats.runIds.value;

  const _reportFilter = new ReportFilter(baseStats.reportFilter.value);
  _reportFilter["componentNames"] = [ component.name ];

  const _cmpData = new CompareData(baseStats.cmpData.value);
  _cmpData.diffType = DiffType.NEW;

  return getStatistics(component, _runIds, _reportFilter, _cmpData);
}

function getResolvedReports(component) {
  const _runIds = baseStats.runIds.value;

  const _reportFilter = new ReportFilter(baseStats.reportFilter.value);
  _reportFilter["componentNames"] = [ component.name ];

  const _cmpData = new CompareData(baseStats.cmpData.value);
  _cmpData.diffType = DiffType.RESOLVED;

  return getStatistics(component, _runIds, _reportFilter, _cmpData);
}

async function fetchStatistics() {
  loading.value = true;
  statistics.value = [];

  components.value = await getComponents();
  initStatistics(components.value);

  statisticsFilters.value = baseStats.getStatisticsFilters();
  const {
    runIds: _runIds,
    reportFilter: _reportFilter,
    cmpData: _cmpData
  } = statisticsFilters.value;

  const _queries = components.value.map(async _component => {
    const _res = await getStatistics(_component, _runIds, _reportFilter,
      _cmpData);

    const _idx = statistics.value.findIndex(_s =>
      _s.component === _component.name);

    statistics.value[_idx] = {
      ..._res,
      loading       : false,
      checkerStatistics: null
    };

    statistics.value = [ ...statistics.value ];

    return statistics.value[_idx];
  });

  await Promise.all(_queries).then(_statistics =>
    statistics.value = _statistics);

  await fetchDifference();

  loading.value = false;
}
</script>
