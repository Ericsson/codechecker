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

<script setup>
import { ReportStatus } from "@cc/report-server-types";

defineProps({
  status: { type: Number, required: true },
  size: { type: Number, default: null }
});
</script>
