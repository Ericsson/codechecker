<template>
  <v-container fluid>
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
        </h3>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <component-statistics-table
          :items="statistics"
          :loading="loading"
          :filters="statisticsFilters"
        />

        <unique-stat-warning v-if="baseStats.reportFilter.value.isUnique" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from "vue";

import { useBaseStatistics } from "@/composables/useBaseStatistics";
import { useToCSV } from "@/composables/useToCSV";
import {
  CompareData,
  DiffType,
  ReportFilter
} from "@cc/report-server-types";

import {
  UniqueStatWarning,
  getComponents,
  initDiffField
} from "@/components/Statistics";
import {
  getComponentStatistics
} from "@/components/Statistics/StatisticsHelper";

import ComponentStatisticsTable from "./ComponentStatisticsTable";

const props = defineProps({
  bus: { type: Object, required: true },
  namespace: { type: String, required: true }
});

const csv = useToCSV();
const baseStats = useBaseStatistics(props, null);

const loading = ref(false);
const statistics = ref([]);
const components = ref([]);
const statisticsFilters = ref({});
const fieldsToUpdate = [ "reports", "unreviewed", "confirmed",
  "falsePositive", "intentional" ];

baseStats.setupRefreshListener(fetchStatistics);

function downloadCSV() {
  const _data = [
    [
      "Component", "Unreviewed", "Confirmed bug",
      "Outstanding reports (Unreviewed + Confirmed)", "False positive",
      "Intentional", "Suppressed reports (False positive + Intentional)",
      "All reports"
    ],
    ...statistics.value.map(_stat => {
      return [
        _stat.component, _stat.unreviewed.count, _stat.confirmed.count,
        _stat.outstanding.count, _stat.falsePositive.count,
        _stat.intentional.count, _stat.suppressed.count, _stat.reports.count
      ];
    })
  ];

  csv.toCSV(_data, "codechecker_component_statistics.csv");
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

function initStatistics(components) {
  statistics.value = components.map(_component => ({
    component     : _component.name,
    value         : _component.value || _component.description,
    reports       : initDiffField(undefined),
    unreviewed    : initDiffField(undefined),
    confirmed     : initDiffField(undefined),
    outstanding   : initDiffField(undefined),
    falsePositive : initDiffField(undefined),
    intentional   : initDiffField(undefined),
    suppressed    : initDiffField(undefined)
  }));
}

async function getStatistics(component, runIds, reportFilter, cmpData) {
  const _res = await getComponentStatistics(component, runIds, reportFilter,
    cmpData);

  return {
    component     : component.name,
    value         : component.value || component.description,
    reports       : initDiffField(_res.reports),
    unreviewed    : initDiffField(_res.unreviewed),
    confirmed     : initDiffField(_res.confirmed),
    outstanding   : initDiffField(_res.outstanding),
    falsePositive : initDiffField(_res.falsePositive),
    intentional   : initDiffField(_res.intentional),
    suppressed    : initDiffField(_res.suppressed)
  };
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
      loading: false,
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

<style lang="scss">
:deep(.v-data-table__expanded__content .v-card) {
  padding: 10px;
}
</style>
