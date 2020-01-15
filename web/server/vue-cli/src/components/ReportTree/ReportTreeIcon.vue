<template>
  <severity-icon
    v-if="item.kind === ReportTreeKind.SEVERITY_LEVEL"
    :status="item.severity"
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

  <v-icon v-else>
    {{ item.open ? "mdi-folder-open" : "mdi-folder" }}
  </v-icon>
</template>

<script>
import VIcon from "Vuetify/VIcon/VIcon";
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
      ReportTreeKind
    };
  },
}
</script>
