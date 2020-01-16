<template>
  <severity-icon
    v-if="item.kind === ReportTreeKind.SEVERITY_LEVEL"
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
import VIcon from "Vuetify/VIcon/VIcon";

import { DetectionStatus } from '@cc/report-server-types';

import { DetectionStatusIcon, SeverityIcon } from '@/components/icons';

import ReportTreeKind from './ReportTreeKind';

export default {
  name: 'ReportTreeIcon',
  components: {
    VIcon,
    DetectionStatusIcon,
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
}
</script>
