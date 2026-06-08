<template>
  <v-btn
    :to="{ name: 'statistics',
           query: {
             ...defaultStatisticsFilterValues,
             ...extraQueries
           }}"
    class="show-statistics"
    title="Show statistics"
    color="green"
    small
    text
    icon
  >
    <v-icon>mdi-chart-line</v-icon>
  </v-btn>
</template>

<script>
import { defaultStatisticsFilterValues } from "@/components/Statistics";

export default {
  name: "ShowStatisticsBtn",
  props: {
    extraQueries: { type: Object, default: () => {} }
  },
  data() {
    return {
      defaultStatisticsFilterValues
    };
  }
};
</script>
