<template>
  <filter-toolbar
    title="Report hash filter"
  >
    <v-card-actions class="">
      <v-text-field
        v-model="reportHash"
        append-icon="mdi-magnify"
        label="Search for report hash (min 5 characters)..."
        single-line
        hide-details
        outlined
        solo
        clearable
        flat
        dense
      />
    </v-card-actions>
  </filter-toolbar>
</template>

<script>
import BaseFilterMixin from "./BaseFilter.mixin";
import FilterToolbar from "./Layout/FilterToolbar";

export default {
  name: "ReportHashFilter",
  components: {
    FilterToolbar
  },
  mixins: [ BaseFilterMixin ],

  data() {
    return {
      id: "report-hash",
      reportHash: null
    };
  },
  watch: {
    reportHash: function () {
      this.updateUrl();
      this.updateReportFilter();
    }
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        reportHash: this.reportHash ? [ `${this.reportHash}*` ] : null
      });
    },

    getUrlState() {
      return {
        [this.id]: this.reportHash
      };
    },

    initByUrl() {
      return new Promise((resolve) => {
        const state = this.$route.query[this.id];
        if (state) {
          this.reportHash = state;
        }

        resolve();
      });
    },
  }
}
</script>
