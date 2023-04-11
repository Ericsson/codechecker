<template>
  <select-option
    :id="id"
    title="Testcase"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    :limit="defaultLimit"
    :multiple="true"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-card-account-details
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { Pair } from "@cc/report-server-types";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "TestcaseFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "testcase",
      search: {
        placeHolder: "Search for testcase names...",
        regexLabel: "Filter by wildcard pattern",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        annotations: this.selectedItems.length == 0
          ? null : this.selectedItems.map(item => new Pair({
            first: "testcase",
            second: item.id
          }))
      });
    },

    onReportFilterChange(key) {
      if (key === "testcaseName") return;
      this.update();
    },

    fetchItems() {
      this.loading = true;

      return new Promise(resolve => {
        ccService.getClient().getReportAnnotations("testcase",
          handleThriftError(res => {
            resolve(res.map(annotation => {
              return {
                id: annotation,
                title: annotation
              };
            }));
            this.loading = false;
          }));
      });
    }
  }
};
</script>
