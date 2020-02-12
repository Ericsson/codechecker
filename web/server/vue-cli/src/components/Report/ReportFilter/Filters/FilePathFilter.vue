<template>
  <select-option
    title="File path"
    :items="items"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    @clear="clear"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-file-document-box-outline
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import { ccService } from "@cc-api";
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
      if (key === "filepath" || !this.selectedItems.length) return;

      this.fetchItems();
    },

    fetchItems(search=null) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.filepath = search ? [ `${search}*` ] : null;

      const limit = 10;
      const offset = null;

      ccService.getClient().getFileCounts(this.runIds, reportFilter,
      this.cmpData, limit, offset, (err, res) => {
        // Order the results alphabetically.
        this.items = Object.keys(res).sort((a, b) => {
            if (a < b) return -1;
            if (a > b) return 1;
            return 0;
        }).map((file) => {
          return {
            id : file,
            title: file,
            count : res[file]
          };
        });

        this.updateSelectedItems();
        this.loading = false;
      });
    },

    filterItems(value) {
      this.fetchItems(value);
    }
  }
}
</script>
