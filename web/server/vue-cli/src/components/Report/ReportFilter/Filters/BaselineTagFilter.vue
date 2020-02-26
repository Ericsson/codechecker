<template>
  <select-option
    title="Tag Filter"
    :items="items"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-tag
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import { ccService } from "@cc-api";
import {
  ReportFilter,
  RunFilter,
  RunHistoryFilter
} from "@cc/report-server-types";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "BaselineTagFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "run-tag",
      search: {
        placeHolder : "Search for run tags...",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    getSelectedItems(tagWithRunNames) {
      return tagWithRunNames.map(s => {
        return new Promise(resolve => {
          this.getTagIds(s).then(tagIds => {
            resolve({
              id: s,
              tagIds: tagIds,
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
            this.selectedItems = res;
            resolve();
          });
        } else {
          resolve();
        }
      });
    },

    updateReportFilter() {
      const selectedTagIds =
        [].concat(...this.selectedItems.map(item => item.tagIds));
      this.setReportFilter({ runTag: selectedTagIds });
    },

    onReportFilterChange(key) {
      if (key === "runTag") return;
      this.update();
    },

    fetchItems(search=null) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter["runTag"] = search ? [ `${search}*` ] : null;

      ccService.getClient().getRunHistoryTagCounts(this.runIds, reportFilter,
        this.cmpData, (err, res) => {
          this.items = res.map(tag => {
            const title = tag.runName + ":" + tag.name;
            return {
              id: title,
              tagIds: [ tag.id ],
              title: title,
              count: tag.count
            };
          });

          this.updateSelectedItems();
          this.loading = false;
        });
    },

    filterItems(value) {
      this.fetchItems(value);
    },

    getTagIds(tagWithRunName) {
      return new Promise(resolve => {
        const index = tagWithRunName.indexOf(":");
        if (index === -1) {
          resolve();
          return;
        }

        const runName = tagWithRunName.substring(0, index);
        const tagName = tagWithRunName.substring(index + 1);

        this.getRunIds(runName).then(runIds => {
          const limit = null;
          const offset = 0;
          const runHistoryFilter = new RunHistoryFilter({
            tagNames: [ tagName ]
          });

          ccService.getClient().getRunHistory(runIds, limit, offset,
            runHistoryFilter, (err, res) => {
              resolve(res.map(history => history.id));
            });
        });
      });
    },

    getRunIds(runName) {
      return new Promise(resolve => {
        const limit = null;
        const offset = null;
        const sortMode = null;
        const runFilter = new RunFilter({ names: [ runName ] });

        ccService.getClient().getRunData(runFilter, limit, offset, sortMode,
          (err, runs) => {
            resolve(runs.map(run => run.runId));
          });
      });
    }
  }
};
</script>
