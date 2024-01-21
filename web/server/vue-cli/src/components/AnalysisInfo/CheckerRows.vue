<template>
  <v-container
    class="analysis-info-checker-rows-in-columns"
  >
    <checker
      v-for="(checker, idx) in checkers"
      :key="idx"
      :name="checker[0]"
      :enabled="checker[1]"
    />
  </v-container>
</template>

<script>
import Checker from "./Checker";

export default {
  name: "CheckerRows",
  components: {
    Checker
  },
  props: {
    checkers: { type: Array, required: true }
  }
};
</script>

<style lang="scss" scoped>
.analysis-info .analysis-info-checker-rows-in-columns {
  columns: 32em auto;
}
</style>
