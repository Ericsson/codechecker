<template>
  <v-chip
    v-if="type === 'macro' || type === 'note'"
    :color="color"
    label
    small
  >
    <span class="font-weight-bold white--text">{{ index }}</span>
  </v-chip>

  <v-avatar
    v-else
    :color="color"
    size="24"
  >
    <span class="caption white--text">{{ index }}</span>
  </v-avatar>
</template>

<script>
export default {
  name: "ReportStepIcon",
  props: {
    type: { type: String, default: null },
    index: { type: [ Number, String ], default: null }
  },
  computed: {
    color() {
      switch (this.type) {
      case "error":
        return "#a94442";
      case "fixit":
        return "#8a6d3b";
      case "macro":
        return "#83876a";
      case "note":
        return "#9299a1";
      default:
        return "#427ea9";
      }
    }
  }
};
</script>
