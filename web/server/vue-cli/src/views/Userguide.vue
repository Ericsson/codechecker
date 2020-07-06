<template>
  <!-- eslint-disable vue/no-v-html -->
  <v-container fluid v-html="doc" />
</template>

<script>
import marked from "marked";

export default {
  name: "Userguide",
  data() {
    return {
      doc: null
    };
  },

  created() {
    import("@/assets/userguide/userguide.md").then(m => {
      this.doc = marked(m.default);
    });
  }
};
</script>
