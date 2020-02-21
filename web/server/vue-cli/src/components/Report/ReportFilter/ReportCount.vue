<template>
  <span>
    <v-icon :color="'#ec7672'">mdi-bug</v-icon>
    <b>{{ value }}</b>
  </span>
</template>

<script>
import { ccService } from "@cc-api";

import { BaseFilterMixin } from "./Filters";

export default {
  name: "ReportCount",
  mixins: [ BaseFilterMixin ],

  data() {
    return {
      id: "report-count",
      value: null
    };
  },

  methods: {
    afterInit() {
      this.getReportCount();
      this.registerWatchers();
    },

    onReportFilterChange() {
      this.getReportCount();
    },

    getReportCount() {
      ccService.getClient().getRunResultCount(this.runIds, this.reportFilter,
      this.cmpData, (err, res) => {
        this.value = res;
      });
    }
  }
}
</script>
