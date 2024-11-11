<template>
  <span
    v-if="numOfNewReports || numOfResolvedReports"
    class="ml-2"
  >
    <v-chip
      v-if="numOfNewReports"
      color="red"
      label
      x-small
      text-color="white"
      class="px-2"
      title="Number of new reports"
      :to="{ name: 'reports', query: {
        ...$router.currentRoute.query,
        ...extraQueryParams,
        'diff-type': 'New'
      }}"
    >
      <v-icon left size="16">
        mdi-arrow-up
      </v-icon>
      {{ numOfNewReports }}
    </v-chip>

    <v-chip
      v-if="numOfResolvedReports"
      color="green"
      label
      x-small
      text-color="white"
      class="px-2"
      title="Number of resolved reports"
      :to="{ name: 'reports', query: {
        ...$router.currentRoute.query,
        ...extraQueryParams,
        'diff-type': 'Resolved'
      }}"
    >
      <v-icon left size="16">
        mdi-arrow-down
      </v-icon>
      {{ numOfResolvedReports }}
    </v-chip>
  </span>
</template>

<script>
export default {
  name: "ReportDiffCount",
  props: {
    numOfNewReports: { type: Number, default: null },
    numOfResolvedReports: { type: Number, default: null },
    extraQueryParams: { type: Object, default: () => {} }
  }
};
</script>