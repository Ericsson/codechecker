<template>
  <select-option
    title="Run Filter"
    :items="items"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-play-circle
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import { ccService } from "@cc-api";
import { ReportFilter, RunFilter } from "@cc/report-server-types";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "BaselineRunFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "run",
      search: {
        placeHolder : "Search for run names (e.g.: myrun*)...",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    getSelectedItems(runNames) {
      return runNames.map((s) => {
        return new Promise((resolve) => {
          this.getRunIdsByRunName(s).then((runIds) => {
            resolve({
              id: s,
              runIds: runIds,
              title: s,
              count: "N/A"
            });
          });
        });
      });
    },

    initByUrl() {
      return new Promise((resolve) => {
        const state = [].concat(this.$route.query[this.id] || []);
        if (state.length) {
          const selectedItems = this.getSelectedItems(state);
          Promise.all(selectedItems).then((res) => {
            this.selectedItems = res;
            resolve();
          });
        } else {
          resolve();
        }
      });
    },

    updateReportFilter() {
      const selectedRunIds =
        [].concat(...this.selectedItems.map(item => item.runIds));
      this.setRunIds(selectedRunIds);
    },

    onRunIdsChange() {},

    onReportFilterChange() {
      this.fetchItems();
    },

    fetchItems(search=null) {
      this.loading = true;

      const runIds = null;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter["runName"] = search ? [ `${search}*` ] : null;

      const limit = null;
      const offset = 0;

      ccService.getClient().getRunReportCounts(runIds, reportFilter, limit,
      offset, (err, res) => {
        this.items = res.map((run) => {
          return {
            id: run.name,
            runIds: [ run.runId ],
            title: run.name,
            count: run.reportCount
          };
        });

        this.updateSelectedItems();
        this.loading = false;
      });
    },

    filterItems(value) {
      this.fetchItems(value);
    },

    getRunIdsByRunName(runName) {
      const runFilter = new RunFilter({ names: [ runName ]});
      const limit = null;
      const offset = null;
      const sortMode = null;

      return new Promise((resolve) => {
        ccService.getClient().getRunData(runFilter, limit, offset, sortMode,
        (err, runs) => {
          resolve(runs.map((run) => run.runId));
        });
      });
    },
  }
}
</script>
