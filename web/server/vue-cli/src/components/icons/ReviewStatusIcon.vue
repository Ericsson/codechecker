<template>
  <v-icon v-if="status === ReviewStatus.UNREVIEWED" color="#4b9fd5">
    mdi-eye-off
  </v-icon>

  <v-icon v-else-if="status === ReviewStatus.CONFIRMED" color="#e92625">
    mdi-check-circle-outline
  </v-icon>

  <v-icon v-else-if="status === ReviewStatus.FALSE_POSITIVE" color="#808080">
    mdi-cancel
  </v-icon>

  <v-icon v-else-if="status === ReviewStatus.INTENTIONAL" color="#669603">
    mdi-close-circle-outline
  </v-icon>
</template>

<script>
import VIcon from "Vuetify/VIcon/VIcon";

import { ReviewStatus } from "@cc/report-server-types";

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
      ReviewStatus
    };
  }
};
</script>
