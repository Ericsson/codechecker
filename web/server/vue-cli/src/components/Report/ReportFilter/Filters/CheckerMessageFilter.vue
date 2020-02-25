<template>
  <select-option
    title="Checker message"
    :items="items"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    @clear="clear"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-message-text-outline
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
  name: "CheckerMessageFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "checker-msg",
      search: {
        placeHolder: "Search for checker messages (e.g.: *deref*)...",
        regexLabel: "Filter by wildcard pattern (e.g.: *deref*)",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        checkerMsg: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "checkerMsg" || !this.selectedItems.length) return;

      this.fetchItems();
    },

    fetchItems(search=null) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.checkerMsg = search ? [ `${search}*` ] : null;

      const limit = 10;
      const offset = null;

      ccService.getClient().getCheckerMsgCounts(this.runIds, reportFilter,
      this.cmpData, limit, offset, (err, res) => {
        this.items = Object.keys(res).map(msg => {
          return {
            id : msg,
            title: msg,
            count : res[msg]
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
};
</script>
