<template>
  <v-icon
    v-if="value === ReportStepIconType.DEFAULT"
    color="#000000"
  >
    mdi-console-line
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.CALLING"
    color="#1855B6"
  >
    mdi-phone-in-talk
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.ENTERED_CALL"
    color="#316ecf"
  >
    mdi-subdirectory-arrow-right
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.RETURNING"
    color="#61a2ff"
  >
    mdi-keyboard-return
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.ASSUMING"
    color="#ff5c11"
  >
    mdi-exclamation-thick
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.ASSUMING_CONDITION"
    color="#7f410c"
  >
    mdi-swap-horizontal-bold
  </v-icon>

  <v-icon
    v-else-if="value === ReportStepIconType.ENTERING_LOOP_BODY"
    color="#000000"
  >
    mdi-refresh
  </v-icon>
  <v-icon
    v-else-if="value === ReportStepIconType.LOOP_BODY_EXECUTED"
    color="#000000"
  >
    mdi-sync
  </v-icon>
  <v-icon
    v-else-if="value === ReportStepIconType.LOOP_BACK"
    color="#000000"
  >
    mdi-undo
  </v-icon>
</template>

<script>
import ReportStepIconType from "./ReportStepIconType";

export default {
  name: "ReportTreeIcon",
  props: {
    value: {
      required: true,
      validator: v => typeof v === "number" || v === null
    }
  },
  data() {
    return {
      ReportStepIconType
    };
  },
};
</script>
