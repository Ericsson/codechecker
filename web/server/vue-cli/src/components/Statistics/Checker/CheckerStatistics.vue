<template>
  <v-container
    fluid
  >
    <v-row>
      <v-col>
        <h3
          class="text-h5 text-primary mb-2"
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
        <checker-statistics-table
          :items="baseStats.statistics.value"
          :loading="loading"
        />

        <unique-stat-warning
          v-if="baseStats.reportFilter.value.isUnique"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from "vue";

import { UniqueStatWarning } from "@/components/Statistics";
import {
  getCheckerStatistics
} from "@/components/Statistics/StatisticsHelper";
import { useBaseStatistics } from "@/composables/useBaseStatistics";
import { useSeverity } from "@/composables/useSeverity";
import { useToCSV } from "@/composables/useToCSV";
import CheckerStatisticsTable from "./CheckerStatisticsTable";

const props = defineProps({
  bus: { type: Object, required: true },
  namespace: { type: String, required: true }
});

const severity = useSeverity();
const csv = useToCSV();
const baseStats = useBaseStatistics(props, getCheckerStatistics);

const loading = ref(false);

baseStats.setupRefreshListener(fetchStatistics);

function downloadCSV() {
  const _data = [
    [
      "Checker", "Severity", "Unreviewed",
      "Confirmed bug", "Outstanding reports (Unreviewed + Confirmed)",
      "False positive", "Intentional",
      "Suppressed reports (False positive + Intentional)", "All reports"
    ],
    ...baseStats.statistics.value.map(_stat => {
      return [
        _stat.checker, severity.severityFromCodeToString(_stat.severity),
        _stat.unreviewed.count, _stat.confirmed.count,
        _stat.outstanding.count, _stat.falsePositive.count,
        _stat.intentional.count, _stat.suppressed.count, _stat.reports.count,
      ];
    })
  ];

  csv.toCSV(_data, "codechecker_checker_statistics.csv");
}

async function fetchStatistics() {
  loading.value = true;

  const {
    runIds: _runIds,
    reportFilter: _reportFilter,
    cmpData: _cmpData
  } = baseStats.getStatisticsFilters();
  baseStats.statistics.value =
    await getCheckerStatistics(_runIds, _reportFilter, _cmpData);

  await baseStats.fetchDifference("checker");

  loading.value = false;
}
</script>
