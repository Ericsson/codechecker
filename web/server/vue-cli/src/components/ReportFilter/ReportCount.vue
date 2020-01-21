<template>
  <span>
    <v-icon :color="'#ec7672'">mdi-bug</v-icon>
    <b>{{ value }}</b>
  </span>
</template>

<script>
import VIcon from "Vuetify/VIcon/VIcon";

import { ccService } from '@cc-api';

import { BaseFilterMixin } from './Filters';

export default {
  name: 'ReportCount',
  components: {
    VIcon
  },
  mixins: [ BaseFilterMixin ],

  data() {
    return {
      id: 'report-count',
      value: null
    };
  },

  methods: {
    afterUrlInit() {
      this.getReportCount();
      this.registerWatchers();
    },

    onReportFilterChange() {
      this.getReportCount();
    },

    getReportCount() {
      const runIds = null;
      const cmpData = null;

      ccService.getClient().getRunResultCount(runIds, this.reportFilter,
      cmpData, (err, res) => {
        this.value = res;
      });
    }
  }
}
</script>
