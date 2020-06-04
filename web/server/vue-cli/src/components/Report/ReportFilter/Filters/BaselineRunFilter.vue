<template>
  <select-option
    :id="id"
    title="Run Filter"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-play-circle
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
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
        placeHolder: "Search for run names (e.g.: myrun*)...",
        regexLabel: "Filter by wildcard pattern (e.g.: myrun*)",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    getSelectedItems(runNames) {
      return runNames.map(s => {
        return new Promise(resolve => {
          this.getRunIdsByRunName(s).then(runIds => {
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
      return new Promise(resolve => {
        const state = [].concat(this.$route.query[this.id] || []);
        if (state.length) {
          const selectedItems = this.getSelectedItems(state);
          Promise.all(selectedItems).then(res => {
            this.setSelectedItems(res, false);
            resolve();
          });
        } else {
          resolve();
        }
      });
    },

    async getSelectedRunIds() {
      return [].concat(...await Promise.all(
        this.selectedItems.map(async item => {
          if (!item.runIds) {
            item.runIds = await this.getRunIdsByRunName(item.title);
          }

          return Promise.resolve(item.runIds);
        })));
    },

    async updateReportFilter() {
      const selectedRunIds = await this.getSelectedRunIds();
      this.setRunIds(selectedRunIds.length ? selectedRunIds : null);
    },

    onRunIdsChange() {},

    onReportFilterChange(key) {
      if (key === "runName") return;
      this.update();
    },

    fetchItems(opt={}) {
      this.loading = true;

      const runIds = null;
      const limit = opt.limit || this.defaultLimit;
      const offset = 0;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter["runName"] = opt.query;

      return new Promise(resolve => {
        ccService.getClient().getRunReportCounts(runIds, reportFilter, limit,
          offset, handleThriftError(res => {
            resolve(res.map(run => {
              return {
                id: run.name,
                runIds: [ run.runId.toNumber() ],
                title: run.name,
                count: run.reportCount.toNumber()
              };
            }));
            this.loading = false;
          }));
      });
    },

    getRunIdsByRunName(runName) {
      const runFilter = new RunFilter({ names: [ runName ] });
      const limit = null;
      const offset = null;
      const sortMode = null;

      return new Promise(resolve => {
        ccService.getClient().getRunData(runFilter, limit, offset, sortMode,
          handleThriftError(runs => {
            resolve(runs.map(run => run.runId.toNumber() ));
          }));
      });
    },
  }
};
</script>
