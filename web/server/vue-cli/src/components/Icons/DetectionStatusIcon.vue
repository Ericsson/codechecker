<template>
  <v-icon
    v-if="status === DetectionStatus.NEW"
    color="#ec7672"
    :title="formattedTitle"
    :size="size"
  >
    mdi-alert-decagram
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.RESOLVED"
    color="#669603"
    :title="formattedTitle"
    :size="size"
  >
    mdi-check
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNRESOLVED"
    color="#007ea7"
    :title="formattedTitle"
    :size="size"
  >
    mdi-bug
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.REOPENED"
    color="#ff0000"
    :title="formattedTitle"
    :size="size"
  >
    mdi-restore
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.OFF"
    color="#4e4e4e"
    :title="formattedTitle"
    :size="size"
  >
    mdi-power
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNAVAILABLE"
    color="#737373"
    :title="formattedTitle"
    :size="size"
  >
    mdi-close
  </v-icon>
</template>

<script>
import { DetectionStatus } from "@cc/report-server-types";
import { DetectionStatusMixin } from "@/mixins";

export default {
  name: "DetectionStatusIcon",
  mixins: [ DetectionStatusMixin ],
  props: {
    status: { type: Number, required: true },
    size: { type: Number, default: null },
    title: { type: String, default: null }
  },

  data() {
    return {
      DetectionStatus
    };
  },

  computed: {
    formattedTitle() {
      if (this.title) return this.title;

      return this.detectionStatusFromCodeToString(this.status);
    }
  }
};
</script>
