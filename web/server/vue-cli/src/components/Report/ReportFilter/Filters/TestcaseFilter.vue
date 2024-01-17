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
import { Pair, ReportFilter } from "@cc/report-server-types";

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

    fetchItems(opt={}) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.annotations = opt.query ? opt.query.map(q => new Pair({
        first: "testcase",
        second: q
      })) : [ new Pair({
        first: "testcase",
        second: null 
      }) ];

      return new Promise(resolve => {
        ccService.getClient().getReportAnnotations(this.runIds, reportFilter,
          this.cmpData, handleThriftError(res => {
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

<style lang="scss" scoped>
.filter-item-title {
  direction: rtl;
  text-align: left;
}
</style>