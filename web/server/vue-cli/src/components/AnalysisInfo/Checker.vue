<template>
  <v-row
    no-gutters
    align="center"
  >
    <v-col
      cols="auto"
    >
      <analyzer-statistics-icon
        class="mr-2"
        :value="(enabled ? 'successful' : 'failed')"
        :title="'\'' + name + '\' ' + (enabled ? 'was' : 'was not') +
          ' enabled in this analysis.'"
      />
    </v-col>
    <v-col
      :class="'pr-1 checker-name ' +
        (enabled ? 'checker-enabled' : 'checker-disabled')"
    >
      {{ name }}
    </v-col>
  </v-row>
</template>

<script>
import { AnalyzerStatisticsIcon } from "@/components/Icons";

export default {
  name: "Checker",
  components: {
    AnalyzerStatisticsIcon
  },
  props: {
    enabled: { type: Boolean, required: true },
    name: { type: String, required: true }
  }
};
</script>
<style lang="scss" scoped>
.analysis-info {
  .checker-name {
    font-family: monospace;
    font-weight: normal;
  }

  .checker-name.checker-enabled {
    color: black;
  }

  .checker-name.checker-disabled {
    color: black;
  }
}
</style>
