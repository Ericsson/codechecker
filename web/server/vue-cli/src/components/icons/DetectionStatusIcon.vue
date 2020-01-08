<template>
  <v-icon v-if="status === DetectionStatus.NEW" color="#ec7672">
    mdi-alert-decagram
  </v-icon>

  <v-icon v-else-if="status === DetectionStatus.RESOLVED" color="#669603">
    mdi-check
  </v-icon>

  <v-icon v-else-if="status === DetectionStatus.UNRESOLVED" color="#007ea7">
    mdi-bug
  </v-icon>

  <v-icon v-else-if="status === DetectionStatus.REOPENED" color="#ff0000">
    mdi-restore
  </v-icon>

  <v-icon v-else-if="status === DetectionStatus.OFF" color="#4e4e4e">
    mdi-power
  </v-icon>

  <v-icon v-else-if="status === DetectionStatus.UNAVAILABLE" color="#737373">
    mdi-close
  </v-icon>
</template>

<script>
import VIcon from "Vuetify/VIcon/VIcon";

import { DetectionStatus } from "@cc/report-server-types";

export default {
  name: "DetectionStatusIcon",
  components: { VIcon },
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
