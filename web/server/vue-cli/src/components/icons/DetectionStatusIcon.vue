<template>
  <v-icon
    v-if="status === DetectionStatus.NEW"
    color="#ec7672"
    title="New"
  >
    mdi-alert-decagram
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.RESOLVED"
    color="#669603"
    title="Resolved"
  >
    mdi-check
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNRESOLVED"
    color="#007ea7"
    title="Unresolved"
  >
    mdi-bug
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.REOPENED"
    color="#ff0000"
    title="Reopened"
  >
    mdi-restore
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.OFF"
    color="#4e4e4e"
    title="Off"
  >
    mdi-power
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNAVAILABLE"
    color="#737373"
    title="Unavailable"
  >
    mdi-close
  </v-icon>
</template>

<script>
import { DetectionStatus } from "@cc/report-server-types";

export default {
  name: "DetectionStatusIcon",
  props: {
    status: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      DetectionStatus
    };
  }
};
</script>
