<template>
  <span
    v-if="item.kind === ReportTreeKind.REPORT_STEPS"
  >
    <report-step-icon
      :value="item.icon"
    />

    <report-step-enum-icon
      :type="item.reportStepIcon.type"
      :index="item.reportStepIcon.index"
    />
  </span>

  <severity-icon
    v-else-if="item.kind === ReportTreeKind.SEVERITY_LEVEL"
    :status="item.severity"
  />

  <detection-status-icon
    v-else-if="item.kind === ReportTreeKind.DETECTION_STATUS"
    :status="DetectionStatus.RESOLVED"
  />

  <detection-status-icon
    v-else-if="item.kind === ReportTreeKind.REPORT"
    :status="item.report.detectionStatus"
  />

  <v-icon
    v-else-if="item.kind === ReportTreeKind.BUG"
  >
    mdi-message-processing
  </v-icon>

  <v-icon
    v-else-if="item.kind === ReportTreeKind.MACRO_EXPANSION"
  >
    mdi-arrow-expand-all
  </v-icon>

  <v-icon
    v-else-if="item.kind === ReportTreeKind.MACRO_EXPANSION_ITEM"
  >
    mdi-arrow-expand
  </v-icon>

  <v-icon
    v-else-if="item.kind === ReportTreeKind.NOTE"
  >
    mdi-note
  </v-icon>

  <v-icon
    v-else-if="item.kind === ReportTreeKind.NOTE_ITEM"
  >
    mdi-note-outline
  </v-icon>

  <v-icon v-else>
    {{ item.open ? "mdi-folder-open" : "mdi-folder" }}
  </v-icon>
</template>

<script>
import { DetectionStatus } from "@cc/report-server-types";

import {
  DetectionStatusIcon,
  ReportStepEnumIcon,
  SeverityIcon
} from "@/components/Icons";

import ReportTreeKind from "./ReportTreeKind";
import ReportStepIcon from "./ReportStepIcon";

export default {
  name: "ReportTreeIcon",
  components: {
    DetectionStatusIcon,
    ReportStepEnumIcon,
    ReportStepIcon,
    SeverityIcon
  },
  props: {
    item: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      DetectionStatus,
      ReportTreeKind
    };
  },
};
</script>
