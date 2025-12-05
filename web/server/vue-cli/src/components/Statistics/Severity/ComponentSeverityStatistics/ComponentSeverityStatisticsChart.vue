<template>
  <Pie
    ref="chart"
    :data="chartData"
    :options="options"
  />
</template>

<script setup>
import { ref, watch } from "vue";

import { useSeverity } from "@/composables/useSeverity";
import { Severity } from "@cc/report-server-types";
import {
  ArcElement,
  Chart as ChartJS,
  Legend,
  Tooltip
} from "chart.js";
import ChartDataLabels from "chartjs-plugin-datalabels";
import { Pie } from "vue-chartjs";

const props = defineProps({
  statistics: { type: Array, required: true },
  loading: { type: Boolean, required: true }
});

ChartJS.register(ArcElement, Tooltip, Legend, ChartDataLabels);

const severity = useSeverity();

const chart = ref();

const severities = [
  Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW,
  Severity.STYLE, Severity.UNSPECIFIED
];

const labels = severities.map(_s => severity.severityFromCodeToString(_s));
const colors = severities.map(_s => severity.severityFromCodeToColor(_s));

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: "bottom"
    },
    datalabels: {
      backgroundColor: colors
    }
  }
};

const chartData = ref({
  labels: labels,
  datasets: [
    {
      data: [],
      backgroundColor: colors,
      datalabels: {
        color: "white",
        borderColor: "white",
        borderRadius: 25,
        borderWidth: 2,
        font: {
          weight: "bold"
        },
      }
    }
  ]
});

watch(
  () => props.statistics,
  () => {
    if (props.loading) return;

    chartData.value = {
      labels: labels,
      datasets: [
        {
          data: props.statistics.reduce((_acc, _curr) => {
            labels.forEach((_s, _idx) => {
              _acc[_idx] += _curr[_s.toLowerCase()].count;
            });
            return _acc;
          }, new Array(labels.length).fill(0)),
          backgroundColor: colors,
          datalabels: {
            color: "white",
            borderColor: "white",
            borderRadius: 25,
            borderWidth: 2,
            font: {
              weight: "bold"
            },
          }
        }
      ]
    };
  },
  { immediate: true }
);
</script>
