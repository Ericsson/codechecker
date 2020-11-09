<template>
  <v-btn
    class="show-report-info-btn"
    color="primary"
    outlined
    small
    v-on="on"
  >
    <v-icon
      class="mr-1"
      small
    >
      mdi-help-circle-outline
    </v-icon>
    Report info
  </v-btn>
</template>

<script>
export default {
  name: "ReportInfoButton",
  props: {
    on: { type: Object, default: null }
  },
};
</script>
