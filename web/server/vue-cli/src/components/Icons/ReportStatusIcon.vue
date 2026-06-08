<template>
  <v-icon
    v-if="status === ReportStatus.OUTSTANDING"
    color="error"
    title="Outstanding"
    :size="size"
  >
    mdi-alert
  </v-icon>

  <v-icon
    v-else-if="status === ReportStatus.CLOSED"
    color="primary"
    title="Closed"
    :size="size"
  >
    mdi-close
  </v-icon>
</template>

<script>
import { ReportStatus } from "@cc/report-server-types";

export default {
  name: "ReportStatusIcon",
  props: {
    status: { type: Number, required: true },
    size: { type: Number, default: null }
  },
  data() {
    return {
      ReportStatus
    };
  }
};
</script>
