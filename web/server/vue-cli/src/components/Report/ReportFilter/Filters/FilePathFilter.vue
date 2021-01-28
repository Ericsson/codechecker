<template>
  <select-option
    :id="id"
    title="File path"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    :limit="defaultLimit"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-file-document-outline
      </v-icon>
    </template>

    <template v-slot:title="{ item }">
      <v-list-item-title
        class="mr-1 filter-item-title"
        :title="`\u200E${item.title}`"
      >
        &lrm;{{ item.title }}&lrm;
      </v-list-item-title>
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter } from "@cc/report-server-types";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "FilePathFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "filepath",
      search: {
        placeHolder: "Search for files (e.g.: */src/*)...",
        regexLabel: "Filter by wildcard pattern (e.g.: */src/*)",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        filepath: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "filepath") return;
      this.update();
    },

    fetchItems(opt={}) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.filepath = opt.query;

      const limit = opt.limit || this.defaultLimit;
      const offset = null;

      return new Promise(resolve => {
        ccService.getClient().getFileCounts(this.runIds, reportFilter,
          this.cmpData, limit, offset, handleThriftError(res => {
          // Order the results alphabetically.
            resolve(Object.keys(res).sort((a, b) => {
              if (a < b) return -1;
              if (a > b) return 1;
              return 0;
            }).map(file => {
              return {
                id : file,
                title: file,
                count : res[file]
              };
            }));
            this.loading = false;
          }));
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.filter-item-title {
  direction: rtl;
  text-align: left;
}
</style>