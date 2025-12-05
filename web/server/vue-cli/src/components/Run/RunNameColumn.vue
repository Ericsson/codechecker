<template>
  <v-list-item two-line>
    <v-list-item-title>
      <router-link
        :to="{ name: 'reports',
               query: {
                 ...defaultReportFilterValues,
                 ...reportFilterQuery
               }
        }"
        class="name mr-2"
      >
        <span>{{ name }}</span>
      </router-link>

      <run-description
        v-if="description"
        :value="description"
      />

      <version-tag
        v-if="versionTag"
        :value="versionTag"
      />
    </v-list-item-title>

    <v-list-item-subtitle>
      <show-statistics-btn
        :extra-queries="statisticsFilterQuery"
      />

      <v-divider
        class="mx-2 d-inline"
        inset
        vertical
      />

      <analysis-info-dialog
        :run-id="runId"
        :icon-only="true"
        icon-size="default"
      />

      <v-divider
        class="mx-2 d-inline"
        inset
        vertical
      />

      <v-btn
        v-for="(value, status) in detectionStatusCount"
        :key="status"
        :to="{ name: 'reports', query: {
          run: name,
          'detection-status': detectionStatusFromCodeToString(status)
        }}"
        class="detection-status-count"
        variant="text"
      >
        <detection-status-icon
          class="mr-1"
          :status="parseInt(status)"
          size="small"
        />
        ({{ value }})
      </v-btn>
    </v-list-item-subtitle>
  </v-list-item>
</template>

<script setup>
import { RunDescription } from "@/components/Run";
import { computed } from "vue";

import { defaultReportFilterValues } from "@/components/Report/ReportFilter";

import { DetectionStatusIcon } from "@/components/Icons";
import { useDetectionStatus } from "@/composables/useDetectionStatus";
import { AnalysisInfoDialog } from "@/components";
import ShowStatisticsBtn from "./ShowStatisticsBtn";
import VersionTag from "./VersionTag";

defineProps({
  runId: { type: Object, required: true },
  name: { type: String, required: true },
  description: { type: String, default: null },
  versionTag: { type: String, default: null },
  detectionStatusCount: { type: Object, default: () => {} },
  showRunHistory: { type: Boolean, default: true },
  openAnalysisInfoDialog: { type: Function, default: () => {} },
  reportFilterQuery: { type: Object, default: () => {} },
  statisticsFilterQuery: { type: Object, default: () => {} },
});

const detectionStatus = useDetectionStatus();

const detectionStatusFromCodeToString = computed(function() {
  return detectionStatus.detectionStatusFromCodeToString;
});
</script>

<style lang="scss" scoped>
.v-list-item__title {
  white-space: normal;
}
</style>