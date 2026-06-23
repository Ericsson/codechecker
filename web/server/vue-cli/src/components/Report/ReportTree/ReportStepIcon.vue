<template>
  <v-icon
    v-if="value === ReportStepIconType.DEFAULT"
    color="#000000"
    :size="size"
  >
    mdi-console-line
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.CALLING"
    color="#1855B6"
    :size="size"
  >
    mdi-phone-in-talk
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.ENTERED_CALL"
    color="#316ecf"
    :size="size"
  >
    mdi-subdirectory-arrow-right
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.RETURNING"
    color="#61a2ff"
    :size="size"
  >
    mdi-keyboard-return
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.ASSUMING"
    color="#ff5c11"
    :size="size"
  >
    mdi-exclamation-thick
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.ASSUMING_CONDITION"
    color="#7f410c"
    :size="size"
  >
    mdi-swap-horizontal-bold
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.ENTERING_LOOP_BODY"
    color="#000000"
    :size="size"
  >
    mdi-refresh
  </v-icon>
  <v-icon
    v-else-if="value === ReportStepIconType.LOOP_BODY_EXECUTED"
    color="#000000"
    :size="size"
  >
    mdi-sync
  </v-icon>
  <v-icon
    v-else-if="value === ReportStepIconType.LOOP_BACK"
    color="#000000"
    :size="size"
  >
    mdi-undo
  </v-icon>
</template>

<script setup>
import ReportStepIconType from "./ReportStepIconType";

defineProps({
  value: {
    required: true,
    validator: v => typeof v === "number" || v === null
  },
  size: {
    type: Number,
    default: undefined
  }
});
</script>
