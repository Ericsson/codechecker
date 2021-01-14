<template>
  <filter-toolbar
    title="Report hash filter"
    :panel="panel"
    @clear="clear(true)"
  >
    <template v-slot:append-toolbar-title>
      <span
        v-if="reportHash"
        class="selected-items"
        :title="reportHash"
      >
        ({{ reportHash }})
      </span>
    </template>

    <v-card-actions class="">
      <v-text-field
        :id="id"
        :value="reportHash"
        append-icon="mdi-magnify"
        label="Search for report hash (min 5 characters)..."
        single-line
        hide-details
        outlined
        solo
        clearable
        flat
        dense
        @input="setReportHash"
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

  methods: {
    setReportHash(reportHash, updateUrl=true) {
      this.reportHash = reportHash;
      this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    updateReportFilter() {
      this.setReportFilter({
        reportHash: this.reportHash ? [ `${this.reportHash}*` ] : null
      });
    },

    getUrlState() {
      return {
        [this.id]: this.reportHash ? this.reportHash : undefined
      };
    },

    initByUrl() {
      return new Promise(resolve => {
        const state = this.$route.query[this.id];
        if (state) {
          this.setReportHash(state, false);
        }

        resolve();
      });
    },

    initPanel() {
      this.panel = this.reportHash !== null;
    },

    clear(updateUrl) {
      this.setReportHash(null, updateUrl);
    }
  }
};
</script>
