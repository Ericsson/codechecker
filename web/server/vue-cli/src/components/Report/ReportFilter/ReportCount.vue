<template>
  <span>
    <v-icon :color="'#ec7672'">mdi-bug</v-icon>
    <b>{{ value }}</b>
  </span>
</template>

<script>
export default {
  name: "ReportCount",
  props: {
    value: { type: Number, required: true }
  },

  data() {
    return {
      id: "report-count"
    };
  }
};
</script>
