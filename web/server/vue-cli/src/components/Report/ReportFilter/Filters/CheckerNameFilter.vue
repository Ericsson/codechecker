<template>
  <select-option
    title="Checker name"
    :items="items"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-account-card-details
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
  name: "CheckerNameFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "checker-name",
      search: {
        placeHolder : "Search for checker names (e.g.: core*)...",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        checkerName: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "checkerName" || !this.selectedItems.length) return;

      this.fetchItems();
    },

    fetchItems(search=null) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.checkerName = search ? [ `${search}*` ] : null;

      const limit = null;
      const offset = 0;

      ccService.getClient().getCheckerCounts(this.runIds, reportFilter,
      this.cmpData, limit, offset, (err, res) => {
        this.items = res.map((checker) => {
          return {
            id: checker.name,
            title: checker.name,
            count: checker.count
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
