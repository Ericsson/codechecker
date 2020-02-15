<template>
  <v-avatar
    :color="color"
    size="28"
  >
    <span class="caption white--text">{{ index }}</span>
  </v-avatar>
</template>

<script>
export default {
  name: "ReportStepIcon",
  props: {
    type: { type: String, default: null },
    index: { type: Number, default: null }
  },
  computed: {
    color() {
      if (this.type === "error") {
        return "#a94442";
      } else if (this.type === "fixit") {
        return "#8a6d3b";
      } else {
        return "#427ea9";
      }
    }
  }
};
</script>
