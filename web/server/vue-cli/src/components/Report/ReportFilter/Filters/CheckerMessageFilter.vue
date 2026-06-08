<template>
  <select-option
    :id="id"
    title="Checker message"
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
        mdi-message-text-outline
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
      if (key === "checkerMsg") return;
      this.update();
    },

    fetchItems(opt={}) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.checkerMsg = opt.query;

      const limit = opt.limit || this.defaultLimit;
      const offset = null;

      return new Promise(resolve => {
        ccService.getClient().getCheckerMsgCounts(this.runIds, reportFilter,
          this.cmpData, limit, offset, handleThriftError(res => {
            resolve(Object.keys(res).map(msg => {
              return {
                id : msg,
                title: msg,
                count: res[msg].toNumber()
              };
            }));
            this.loading = false;
          }));
      });
    }
  }
};
</script>
