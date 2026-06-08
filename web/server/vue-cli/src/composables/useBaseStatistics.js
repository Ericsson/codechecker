import { computed, onActivated, onDeactivated, ref } from "vue";
import { useStore } from "vuex";

import { CompareData, DiffType, ReportFilter } from "@cc/report-server-types";

export function useBaseStatistics(props, getStatisticsFunction) {
  const store = useStore();
  const statistics = ref([]);

  const runIds = computed(function() {
    return store.getters[`${props.namespace}/getRunIds`];
  });

  const reportFilter = computed(function() {
    return store.getters[`${props.namespace}/getReportFilter`];
  });

  const cmpData = computed(function() {
    return store.getters[`${props.namespace}/getCmpData`];
  });

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

  function updateStatistics(reports, name, type) {
    const _fieldToUpdate = [ "reports", "unreviewed", "confirmed",
      "falsePositive", "intentional" ];

    statistics.value.forEach(_s => {
      const _row = reports.find(_n => _n[name] === _s[name]);
      if (_row) {
        _fieldToUpdate.forEach(_f => _s[_f][type] = _row[_f].count);
        updateCalculatedFields(_s, _row, type);
      }
    });
  }

  function getNewReports() {
    const _runIds = runIds.value;
    const _reportFilter = reportFilter.value;
    const _cmpData = new CompareData(cmpData.value);
    _cmpData.diffType = DiffType.NEW;

    return getStatisticsFunction(_runIds, _reportFilter, _cmpData);
  }

  function getResolvedReports() {
    const _runIds = runIds.value;
    const _reportFilter = reportFilter.value;
    const _cmpData = new CompareData(cmpData.value);
    _cmpData.diffType = DiffType.RESOLVED;

    return getStatisticsFunction(_runIds, _reportFilter, _cmpData);
  }

  async function fetchDifference(name) {
    if (!cmpData.value) return;

    const _q1 = getNewReports().then(_newReports => {
      updateStatistics(_newReports, name, "new");
    });

    const _q2 = getResolvedReports().then(_resolvedReports => {
      updateStatistics(_resolvedReports, name, "resolved");
    });

    return Promise.all([ _q1, _q2 ]);
  }

  function getStatisticsFilters() {
    let _runIds = runIds.value;
    let _reportFilter = reportFilter.value;
    const _cmpData = null;

    if (cmpData.value) {
      _runIds = cmpData.value.runIds;
      _reportFilter = new ReportFilter(reportFilter.value);
      _reportFilter.runTag = cmpData.value.runTag;
    }

    return {
      runIds: _runIds,
      reportFilter: _reportFilter,
      cmpData: _cmpData
    };
  }

  function setupRefreshListener(fetchStatistics) {
    onActivated(function() {
      props.bus.on("refresh", fetchStatistics);
    });

    onDeactivated(function() {
      props.bus.off("refresh", fetchStatistics);
    });
  }

  return {
    statistics,
    runIds,
    reportFilter,
    cmpData,
    fetchDifference,
    getStatisticsFilters,
    setupRefreshListener
  };
}
