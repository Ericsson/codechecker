<template>
  <select-option
    :id="id"
    title="Analyzer name"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-crosshairs
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter } from "@cc/report-server-types";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "AnalyzerNameFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "analyzer-name",
      search: {
        placeHolder: "Search for analyzer names (e.g.: clang*)...",
        regexLabel: "Filter by wildcard pattern (e.g.: clang*)",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        analyzerNames: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "analyzerNames") return;
      this.update();
    },

    fetchItems(opt={}) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.analyzerNames = opt.query;

      const limit = opt.limit || this.defaultLimit;
      const offset = null;

      return new Promise(resolve => {
        ccService.getClient().getAnalyzerNameCounts(this.runIds, reportFilter,
          this.cmpData, limit, offset, handleThriftError(res => {
          // Order the results alphabetically.
            resolve(Object.keys(res).sort((a, b) => {
              if (a < b) return -1;
              if (a > b) return 1;
              return 0;
            }).map(analyzerName => {
              return {
                id : analyzerName,
                title: analyzerName,
                count : res[analyzerName]
              };
            }));
            this.loading = false;
          }));
      });
    }
  }
};
</script>
