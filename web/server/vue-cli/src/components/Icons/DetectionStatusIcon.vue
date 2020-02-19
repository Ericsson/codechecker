<template>
  <v-icon
    v-if="status === DetectionStatus.NEW"
    color="#ec7672"
    title="New"
    :size="size"
  >
    mdi-alert-decagram
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.RESOLVED"
    color="#669603"
    title="Resolved"
    :size="size"
  >
    mdi-check
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNRESOLVED"
    color="#007ea7"
    title="Unresolved"
    :size="size"
  >
    mdi-bug
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.REOPENED"
    color="#ff0000"
    title="Reopened"
    :size="size"
  >
    mdi-restore
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.OFF"
    color="#4e4e4e"
    title="Off"
    :size="size"
  >
    mdi-power
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNAVAILABLE"
    color="#737373"
    title="Unavailable"
    :size="size"
  >
    mdi-close
  </v-icon>
</template>

<script>
import { DetectionStatus } from "@cc/report-server-types";

export default {
  name: "DetectionStatusIcon",
  props: {
    status: { type: Number, required: true },
    size: { type: Number, default: null }
  },
  data() {
    return {
      DetectionStatus
    };
  }
};
</script>
