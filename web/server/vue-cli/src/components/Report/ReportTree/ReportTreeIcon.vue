<template>
  <span
    v-if="item.kind === ReportTreeKind.REPORT_STEPS"
  >
    <report-step-icon
      :value="item.icon"
      :size="size"
    />

    <report-step-enum-icon
      :type="item.reportStepIcon.type"
      :index="item.reportStepIcon.index"
      :size="size"
    />
  </span>

  <severity-icon
    v-else-if="item.kind === ReportTreeKind.SEVERITY_LEVEL"
    :status="item.severity"
    :size="size"
  />

  <detection-status-icon
    v-else-if="item.kind === ReportTreeKind.DETECTION_STATUS"
    :status="DetectionStatus.RESOLVED"
    :size="size"
  />

  <detection-status-icon
    v-else-if="item.kind === ReportTreeKind.REPORT"
    :status="item.report.detectionStatus"
    :size="size"
  />

  <v-icon
    v-else-if="item.kind === ReportTreeKind.BUG"
    :size="size"
  >
    mdi-message-processing
  </v-icon>

  <v-icon
    v-else-if="item.kind === ReportTreeKind.MACRO_EXPANSION"
    :size="size"
  >
    mdi-arrow-expand-all
  </v-icon>

  <v-icon
    v-else-if="item.kind === ReportTreeKind.MACRO_EXPANSION_ITEM"
    :size="size"
  >
    mdi-arrow-expand
  </v-icon>

  <v-icon
    v-else-if="item.kind === ReportTreeKind.NOTE"
    :size="size"
  >
    mdi-note
  </v-icon>

  <v-icon
    v-else-if="item.kind === ReportTreeKind.NOTE_ITEM"
    :size="size"
  >
    mdi-note-outline
  </v-icon>

  <v-icon
    v-else-if="item.isOutstanding"
    title="Outstanding reports, that are potential bugs
(review status is unreviewed or confirmed and
detection status is new, unresolved or reopened)"
    color="primary"
    :size="size"
  >
    mdi-folder-lock-open
  </v-icon>

  <v-icon
    v-else-if="!item.isOutstanding"
    title="Closed reports, that are fixed bugs, suppressed reports
(false positive, intentional) or whose detection status is resolved,
off or unavailable."
    color="primary"
    :size="size"
  >
    mdi-folder-lock
  </v-icon>

  <v-icon
    v-else
    :size="size"
  >
    {{ item.open ? "mdi-folder-open" : "mdi-folder" }}
  </v-icon>
</template>

<script setup>
import { DetectionStatus } from "@cc/report-server-types";

import {
  DetectionStatusIcon,
  ReportStepEnumIcon,
  SeverityIcon
} from "@/components/Icons";

import ReportStepIcon from "./ReportStepIcon";
import ReportTreeKind from "./ReportTreeKind";

defineProps({
  item: { type: Object, required: true },
  size: { type: Number, default: null }
});
</script>
