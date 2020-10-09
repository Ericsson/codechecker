<template>
  <v-avatar
    v-if="status === Severity.UNSPECIFIED"
    tile
    :color="color"
    :size="size"
    title="Unspecified"
  >
    <span class="white--text font-weight-bold">U</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.STYLE"
    tile
    :color="color"
    :size="size"
    title="Style"
  >
    <span class="white--text font-weight-bold">S</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.LOW"
    tile
    :color="color"
    :size="size"
    title="Low"
  >
    <span class="white--text font-weight-bold">L</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.MEDIUM"
    tile
    :color="color"
    :size="size"
    title="Medium"
  >
    <span class="white--text font-weight-bold">M</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.HIGH"
    tile
    :color="color"
    :size="size"
    title="High"
  >
    <span class="white--text font-weight-bold">H</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.CRITICAL"
    tile
    :color="color"
    :size="size"
    title="Critical"
  >
    <span class="white--text font-weight-bold">C</span>
  </v-avatar>
</template>

<script>
import { Severity } from "@cc/report-server-types";
import { SeverityMixin } from "@/mixins";

export default {
  name: "SeverityIcon",
  mixins: [ SeverityMixin ],
  props: {
    status: { type: Number, required: true },
    size: { type: Number, default: 24 }
  },
  data() {
    return {
      Severity,
      color: this.severityFromCodeToColor(this.status)
    };
  }
};
</script>
