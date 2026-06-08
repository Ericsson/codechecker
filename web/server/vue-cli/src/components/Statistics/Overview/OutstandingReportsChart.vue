<template>
  <div
    class="lineChart"
  >
    <Line
      ref="chart"
      :data="chartData"
      :options="options"
    />
  </div>
</template>

<script setup>
import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import ChartDataLabels from "chartjs-plugin-datalabels";
import {
  endOfDay, endOfMonth, endOfToday, endOfWeek, endOfYear,
  format, subDays, subMonths, subWeeks, subYears
} from "date-fns";
import _ from "lodash";
import { onActivated, onDeactivated, onMounted, ref, watch } from "vue";
import { Line } from "vue-chartjs";
import { useRouter } from "vue-router";

import { useDateUtils } from "@/composables/useDateUtils";
import { useSeverity } from "@/composables/useSeverity";
import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter, Severity } from "@cc/report-server-types";

const props = defineProps({
  bus: { type: Object, required: true },
  getStatisticsFilters: { type: Function, required: true },
  interval: { type: String, required: true },
  resolution: { type: String, required: true },
});

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartDataLabels
);

const router = useRouter();
const dateUtils = useDateUtils();
const severity = useSeverity();

const chart = ref();
const dates = ref([]);
const filterDateFormat = ref("");

const refreshHandler = () => fetchDataHandler();

const options = ref({
  plugins: {
    legend: {
      display: true,
    },
    tooltip: {
      mode: "index",
      callbacks: {
        footer: function (_tooltipItems) {
          const _total =
            _tooltipItems.reduce((_acc, _curr) => _acc + _curr.raw, 0);

          return `Total: ${_total}`;
        },
      },
      intersect: false
    },
    hover: {
      mode: "nearest",
      intersect: true
    }
  },
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      ticks: {
        padding: 10
      }
    },
    y: {
      beginAtZero: true,
      min: 0,
      max: 100
    }
  },
  onClick: (event, elements, chart) => {
    if (elements.length > 0) {
      const elementIndex = elements[0].index;
      const datasetIndex = elements[0].datasetIndex;

      const runName = router.currentRoute.value.query["run"];
      const severity = chart.data.datasets[datasetIndex].label;
      // Creating a local copy of dates since reverse mutates the array.
      let localDates = dates.value;
      localDates = localDates.reverse()[elementIndex];
      const formattedDate =
        new Date(format(localDates, filterDateFormat.value));
      let reportsDate;
      if (props.resolution === "days") {
        reportsDate = endOfDay(formattedDate);
      } else if (props.resolution === "weeks") {
        reportsDate = endOfWeek(formattedDate);
      } else if (props.resolution === "months") {
        reportsDate = endOfMonth(formattedDate);
      } else if (props.resolution === "years") {
        reportsDate = endOfYear(formattedDate);
      }

      router.push({
        name: "reports",
        query: {
          "run": runName,
          "is-unique": "off",
          "diff-type": "New",
          "open-reports-date": `${dateUtils.dateTimeToStr(reportsDate)}`,
          "severity": severity
        }
      });
    }
  },
  onHover: (event, elements) => {
    event.native.target.style.cursor = elements.length ? "pointer" : "default";
  }
});

const chartData = ref({
  labels: [],
  datasets: [
    ...Object.keys(Severity).reverse().map(_s => {
      const _severityId = Severity[_s];
      const _color = severity.severityFromCodeToColor(_severityId);

      return {
        type: "line",
        label: severity.severityFromCodeToString(_severityId),
        backgroundColor: _color,
        borderColor: _color,
        borderWidth: 3,
        fill: false,
        tension: 0.2,
        pointRadius: 5,
        pointHoverRadius: 10,
        datalabels: {
          backgroundColor: _color,
          color: "white",
          borderRadius: 4,
          font: {
            weight: "bold"
          },
        },
        data: []
      };
    })
  ]
});

watch(function() { return props.interval; }, _.debounce(function() {
  setChartData();
  fetchData(dates.value);
}, 500));

watch(function() { return props.resolution; }, function() {
  setChartData();
  fetchData(dates.value);
});

onMounted(function() {
  setChartData();
});

onActivated(function() {
  props.bus.on("refresh", refreshHandler);
});

onDeactivated(function() {
  props.bus.off("refresh", refreshHandler);
});

function fetchDataHandler() {
  fetchData(dates.value);
}

/* eslint-disable no-unused-vars */
function setChartDataOld() {
  const _interval = parseInt(props.interval);
  if (isNaN(_interval) || _interval <=0)
    return;

  let _dateFormat = "yyyy. MMM. dd";
  filterDateFormat.value = "yyyy-MM-dd";

  if (props.resolution === "days") {
    const _today = endOfToday();
    dates.value = [ ...new Array(_interval).keys() ].map(_i =>
      subDays(_today, _i));
  }
  else if (props.resolution === "weeks") {
    const _endOfCurrentWeek = endOfWeek(new Date(), { weekStartsOn: 1 });
    dates.value = [ ...new Array(_interval).keys() ].map(_i =>
      subWeeks(_endOfCurrentWeek, _i));
  }
  else if (props.resolution === "months") {
    const _endOfCurrentMonth = endOfMonth(new Date());
    dates.value = [ ...new Array(_interval).keys() ].map(_i =>
      subMonths(_endOfCurrentMonth, _i));

    _dateFormat = "yyyy. MMM";
    filterDateFormat.value = "yyyy-MM";
  }
  else if (props.resolution === "years") {
    const _endOfCurrentYear = endOfYear(new Date());
    dates.value = [ ...new Array(_interval).keys() ].map(_i =>
      subYears(_endOfCurrentYear, _i));

    _dateFormat = "yyyy";
    filterDateFormat.value = "yyyy";
  }

  chartData.value.labels = [ ...dates.value ].reverse().map((_d, _idx) => {
    const _date = format(_d, _dateFormat);
    if (_idx === dates.value.length - 1)
      return `${_date} (Current)`;
    return _date;
  });

  chartData.value.datasets.forEach(_d => {
    if (dates.value.length > _d.data.length) {
      _d.data = [
        ...new Array(dates.value.length - _d.data.length).fill(0),
        ..._d.data
      ];
    } else {
      _d.data = _d.data.slice(_d.data.length - dates.value.length,
        _d.data.length);
    }
  });

  chartData.value = { ...chartData.value };
}

function setChartData() {
  const _interval = parseInt(props.interval);
  if (isNaN(_interval) || _interval <=0)
    return;

  let _dateFormat = "yyyy. MMM. dd";
  filterDateFormat.value = "yyyy-MM-dd";

  if (props.resolution === "days") {
    const _today = endOfToday();
    dates.value = [ ...new Array(_interval).keys() ].map(_i =>
      subDays(_today, _i));
  }
  else if (props.resolution === "weeks") {
    const _endOfCurrentWeek = endOfWeek(new Date(), { weekStartsOn: 1 });
    dates.value = [ ...new Array(_interval).keys() ].map(_i =>
      subWeeks(_endOfCurrentWeek, _i));
  }
  else if (props.resolution === "months") {
    const _endOfCurrentMonth = endOfMonth(new Date());
    dates.value = [ ...new Array(_interval).keys() ].map(_i =>
      subMonths(_endOfCurrentMonth, _i));

    _dateFormat = "yyyy. MMM";
    filterDateFormat.value = "yyyy-MM";
  }
  else if (props.resolution === "years") {
    const _endOfCurrentYear = endOfYear(new Date());
    dates.value = [ ...new Array(_interval).keys() ].map(_i =>
      subYears(_endOfCurrentYear, _i));

    _dateFormat = "yyyy";
    filterDateFormat.value = "yyyy";
  }

  const newLabels = [ ...dates.value ].reverse().map((_d, _idx) => {
    const _date = format(_d, _dateFormat);
    if (_idx === dates.value.length - 1)
      return `${_date} (Current)`;
    return _date;
  });

  const newDatasets = chartData.value.datasets.map(_d => ({
    ..._d,
    data: new Array(dates.value.length).fill(0)
  }));

  chartData.value = {
    labels: newLabels,
    datasets: newDatasets
  };
}

async function fetchData(datesToUpdate) {
  const dataColumns = await Promise.all(
    dates.value.map(async (_d, _idx) => {
      if (!datesToUpdate.includes(_d)) return null;
      const _reportCount = await fetchOutstandingReports(_d);
      return { _reportCount, _idx };
    })
  );

  dataColumns.forEach(col => {
    if (!col) return;
    const { _reportCount, _idx } = col;
    
    Object.keys(Severity).reverse().forEach((_s, _i) => {
      const _severityId = Severity[_s];
      const _numOfReports = _reportCount[_severityId]?.toNumber() || 0;
      const _data = chartData.value.datasets[_i].data;
      _data[_data.length - 1 - _idx] = _numOfReports;
    });
  });

  chartData.value = { ...chartData.value };

  const allValues = chartData.value.datasets.flatMap(d => d.data);
  const maxValue = Math.max(...allValues);
  options.value.scales.y.max = Math.ceil(maxValue * 1.1);
  options.value = { ...options.value };
}

function fetchOutstandingReports(date) {
  const {
    runIds: _runIds,
    reportFilter: _reportFilter
  } = props.getStatisticsFilters();

  const _rFilter = new ReportFilter(_reportFilter);
  _rFilter.openReportsDate = dateUtils.getUnixTime(date);
  _rFilter.detectionStatus = null;

  const _cmpData = null;

  return new Promise(_resolve => {
    ccService.getClient().getSeverityCounts(
      _runIds,
      _rFilter,
      _cmpData,
      handleThriftError(_res => _resolve(_res)));
  });
}
</script>

<style lang="css">
  .lineChart {
    height: 800px;
  }
</style>
