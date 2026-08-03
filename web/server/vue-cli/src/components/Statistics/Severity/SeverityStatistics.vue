<template>
  <v-container fluid>
    <v-col>
      <v-row class="ma-0 mb-4">
        <h3 class="title text-primary">
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
      </v-row>
      <v-row class="ma-0 mb-6">
        <v-col
          cols="12"
          class="pa-0"
        >
          <div class="text-h6 mb-4">
            Severity statistics
            <tooltip-help-icon>
              This table shows severity statistics for the product.
              <br><br>
              The following filters don't affect these values:
              <ul>
                <li><b>Severity</b> filter.</li>
                <li><b>Source component</b> filter.</li>
              </ul>
            </tooltip-help-icon>
          </div>
          <severity-statistics-table
            :items="statistics"
            :loading="loading"
          />
          <unique-stat-warning
            v-if="baseStats.reportFilter.value.isUnique"
          />
        </v-col>
      </v-row>
      <v-row class="ma-0">
        <v-col
          cols="12"
          class="pa-0"
        >
          <component-severity-statistics
            :bus="bus"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-container>
</template>

<script setup>
import { ref } from "vue";

import { useBaseStatistics } from "@/composables/useBaseStatistics";
import { useSeverity } from "@/composables/useSeverity";
import { useToCSV } from "@/composables/useToCSV";

import { UniqueStatWarning } from "@/components/Statistics";
import {
  getSeverityStatistics
} from "@/components/Statistics/StatisticsHelper";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { ComponentSeverityStatistics } from "./ComponentSeverityStatistics";

import SeverityStatisticsTable from "./SeverityStatisticsTable";

const props = defineProps({
  bus: { type: Object, required: true }
});

const severity = useSeverity();
const csv = useToCSV();
const baseStats = useBaseStatistics(props, getSeverityStatistics);

const loading = ref(false);
const statistics = ref([]);

baseStats.setupRefreshListener(fetchStatistics);

function downloadCSV() {
  const _data = [
    [ "Severity", "Unreviewed", "Confirmed bug",
      "Outstanding reports (Unreviewed + Confirmed)", "False positive",
      "Intentional", "Suppressed reports (False positive + Intentional)",
      "All reports"
    ],
    ...statistics.value.map(_stat => {
      return [
        severity.severityFromCodeToString(_stat.severity),
        _stat.unreviewed.count, _stat.confirmed.count,
        _stat.outstanding.count, _stat.falsePositive.count,
        _stat.intentional.count, _stat.suppressed.count, _stat.reports.count
      ];
    })
  ];

  csv.toCSV(_data, "codechecker_severity_statistics.csv");
}

async function fetchStatistics() {
  loading.value = true;

  const {
    runIds: _runIds,
    reportFilter: _reportFilter,
    cmpData: _cmpData
  } = baseStats.getStatisticsFilters();
  statistics.value =
    await getSeverityStatistics(_runIds, _reportFilter, _cmpData);

  await baseStats.fetchDifference("severity");

  loading.value = false;
}
</script>

<style>
.severity {
  text-decoration: none;
}
</style>
