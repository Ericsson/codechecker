<template>
  <select-option
    :id="id"
    title="Run / Tag Filter"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    :apply="apply"
    @select="prevSelectedRuns = $event"
    @clear="clear(true)"
    @on-menu-show="onMenuShow"
  >
    <template v-slot:append-toolbar-title>
      <selected-toolbar-title-items
        v-if="selectedToolbarTitleItems.length"
        :value="selectedToolbarTitleItems"
      />
    </template>

    <template
      v-slot:menu-content="{ items, prevSelectedItems, cancel, select }"
    >
      <v-tabs
        v-model="tab"
        fixed-tabs
        hide-slider
      >
        <v-tab>Select Runs</v-tab>
        <v-tab
          :disabled="prevSelectedRuns.length === 0"
          class="tags"
          @click="specifyTagsTab"
        >
          Select Tags
          <v-tooltip max-width="200" right>
            <template v-slot:activator="{ on }">
              <v-icon
                color="accent"
                class="ml-1"
                small
                v-on="on"
              >
                mdi-help-circle
              </v-icon>
            </template>

            <span>
              Specify run tags of the selected runs to filter reports that
              were <i>DETECTED</i> and <i>NOT FIXED BEFORE</i> the date when
              the selected tag was created.
            </span>
          </v-tooltip>
        </v-tab>

        <v-tab-item class="run-tab-item">
          <items
            :items="items"
            :selected-items="prevSelectedItems"
            :search="search"
            :limit="defaultLimit"
            @apply="apply"
            @cancel="cancel"
            @select="select"
            @update:items="items.splice(0, items.length, ...$event)"
          >
            <template v-slot:icon>
              <v-icon color="grey">
                mdi-play-circle
              </v-icon>
            </template>
          </items>
        </v-tab-item>
        <v-tab-item class="tag-tab-item">
          <baseline-tag-items
            :namespace="namespace"
            :bus="bus"
            :load-event-bus="tabEventBus"
            :selected-items="selectedTagItems"
            :selected-run-items="prevSelectedItems"
            :fetch-tags="fetchTags"
            @apply="apply"
            @cancel="cancel"
            @select="selectRunTags"
            @back-to-runs="backToRunsTab"
          >
            <template v-slot:icon>
              <v-icon color="grey">
                mdi-tag
              </v-icon>
            </template>
          </baseline-tag-items>
        </v-tab-item>
      </v-tabs>
    </template>

    <template>
      <items-selected
        :selected-items="selectedItems"
        @update:select="updateSelectedItems"
      >
        <template v-slot:icon>
          <v-icon color="grey">
            mdi-play-circle
          </v-icon>
        </template>

        <template v-slot:title="{ item }">
          {{ titles[item.title] }}
        </template>
      </items-selected>
    </template>
  </select-option>
</template>

<script>
import Vue from "vue";
import _ from "lodash";

import { ccService, handleThriftError } from "@cc-api";
import {
  ReportFilter,
  RunFilter,
  RunHistoryFilter
} from "@cc/report-server-types";

import {
  Items,
  ItemsSelected,
  SelectOption,
  SelectedToolbarTitleItems,
  filterIsChanged
} from "./SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";
import BaselineTagItems from "./BaselineTagItems";

export default {
  name: "BaselineRunFilter",
  components: {
    BaselineTagItems,
    Items,
    ItemsSelected,
    SelectOption,
    SelectedToolbarTitleItems
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "run",
      runTagId: "run-tag",
      tab: null,
      tabEventBus: new Vue(),
      prevSelectedRuns: [],
      selectedTagItems: [],
      prevSelectedTagItems: [],
      search: {
        placeHolder: "Search for run names (e.g.: myrun*)...",
        regexLabel: "Filter by wildcard pattern (e.g.: myrun*)",
        filterItems: this.filterItems
      }
    };
  },

  computed: {
    titles() {
      return this.selectedItems.reduce((acc, curr) => {
        const tagNames = this.selectedTagItems
          .filter(s => curr.runIds.includes(s.runId))
          .map(s => s.tagName);

        const title = tagNames.length
          ? `${curr.title}:${tagNames.join(",")}`
          : curr.title;

        return {
          ...acc,
          [curr.title]: title
        };
      }, {});
    },

    selectedToolbarTitleItems() {
      return this.selectedItems.map(item => ({
        title: this.titles[item.title]
      }));
    }
  },

  methods: {
    onMenuShow() {
      this.tab = null;
    },

    backToRunsTab() {
      this.tab = null;
    },

    specifyTagsTab() {
      this.tabEventBus.$emit("reload");
    },

    runFilterIsChanged() {
      return filterIsChanged(this.prevSelectedRuns, this.selectedItems);
    },

    tagFilterIsChanged() {
      return filterIsChanged(this.prevSelectedTagItems, this.selectedTagItems);
    },

    updateSelectedItems(selectedRunItems) {
      this.setSelectedItems(selectedRunItems, this.selectedTagItems);
    },

    getSelectedRunItems(runNames) {
      return Promise.all(runNames.map(async s => ({
        id: s,
        runIds: await this.getRunIds(s),
        title: s,
        count: "N/A"
      })));
    },

    async getSelectedTagItems(tags) {
      const tagIds = [];
      const tagWithRunNames = [];
      tags.forEach(t => {
        const id = +t;
        if (isNaN(id)) {
          tagWithRunNames.push(t);
        } else {
          tagIds.push(id);
        }
      });

      // Get tags by tag ids.
      const tags1 = tagIds.length
        ? (await this.getTags(tagIds)).map(t => ({
          id: t.id.toNumber(),
          runName: t.runName,
          runId: t.runId.toNumber(),
          tagName : t.versionTag,
          title: t.versionTag,
          count: "N/A"
        }))
        : [];

      // Get tags by tag names (backward compatibility).
      const tags2 = tagWithRunNames.length
        ? (await Promise.all(tagWithRunNames.map(async s => {
          const { runName, tagName } = this.extractTagWithRunName(s);
          const tags = await this.getTags(null, s);
          return {
            id: tags[0].id,
            runName: runName ? runName : tags[0].runName,
            runId: tags[0].runId.toNumber(),
            tagName,
            title: s,
            count: "N/A"
          };
        })))
        : [];

      return tags1.concat(tags2);
    },

    async initByUrl() {
      const runs = [].concat(this.$route.query[this.id] || []);
      const tags = [].concat(this.$route.query[this.runTagId] || []);

      if (runs.length || tags.length) {
        const selectedRuns = await this.getSelectedRunItems(runs);
        const selectedTags = await this.getSelectedTagItems(tags);

        await this.setSelectedItems(selectedRuns, selectedTags, false);
      }
    },

    apply(selectedRunItems) {
      if (!this.runFilterIsChanged() && !this.tagFilterIsChanged()) return;

      this.setSelectedItems(selectedRunItems, this.prevSelectedTagItems);
    },

    async clear(updateUrl) {
      await this.setSelectedItems([], [], updateUrl);
    },

    selectRunTags(selectedItems) {
      this.prevSelectedTagItems = selectedItems;
    },

    getUrlState() {
      const runState =
        this.selectedItems.map(item => this.encodeValue(item.id));

      const tagState =
        this.selectedTagItems.map(item => item.id);

      return {
        [this.id]: runState.length ? runState : undefined,
        [this.runTagId]: tagState.length ? tagState : undefined
      };
    },

    async setSelectedItems(runItems, tagItems, updateUrl=true) {
      this.selectedItems = runItems;

      // When removing a run with tag item from the selected filter list
      // we need to remove the tags too.
      this.selectedTagItems = tagItems.filter(t =>
        runItems.findIndex(s => s.runIds.includes(t.runId)) > -1);
      this.prevSelectedTagItems = _.cloneDeep(this.selectedTagItems);

      await this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    async getSelectedRunIds() {
      return [].concat(...await Promise.all(
        this.selectedItems.map(async item => {
          if (!item.runIds) {
            item.runIds = await this.getRunIds(item.title);
          }

          return Promise.resolve(item.runIds);
        })));
    },

    async updateReportFilter() {
      const selectedRunIds = await this.getSelectedRunIds();
      this.setRunIds(selectedRunIds.length ? selectedRunIds : null);

      const selectedTagIds = this.selectedTagItems.map(t => t.id);
      this.reportFilter.runTag = selectedTagIds.length ? selectedTagIds : null;
    },

    onRunIdsChange() {},

    onReportFilterChange(key) {
      if (key === "runName" || key === "runTag") return;
      this.update();
    },

    fetchItems(opt={}) {
      this.loading = true;

      const runIds = null;
      const limit = opt.limit || this.defaultLimit;
      const offset = 0;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.runName = opt.query;
      reportFilter.runTag = null;

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

    getRunIds(runName) {
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

    async fetchTags(opt={}) {
      this.loading = true;
      this.filterOpt = opt;

      const reportFilter = new ReportFilter(this.reportFilter);

      const limit = opt.limit || this.defaultLimit;
      const offset = 0;

      reportFilter.runTag = opt.query
        ? (await Promise.all(opt.query?.map(s => this.getTagIds(s)))).flat()
        : null;

      const runIds = (await Promise.all(this.prevSelectedRuns.map(async r => {
        if (!r.runIds) {
          r.runIds = await this.getRunIds(r.id);
        }

        return r.runIds;
      }))).flat();

      return new Promise(resolve => {
        ccService.getClient().getRunHistoryTagCounts(runIds, reportFilter,
          null, limit, offset, handleThriftError(res => {
            resolve(res.map(tag => {
              const title = tag.runName + ":" + tag.name;
              const id = tag.id.toNumber();
              return {
                id,
                runName: tag.runName,
                runId: tag.runId.toNumber(),
                tagName: tag.name,
                title: title,
                count: tag.count.toNumber()
              };
            }));
            this.loading = false;
          }));
      });
    },

    extractTagWithRunName(runWithTagName) {
      const index = runWithTagName.indexOf(":");

      let runName, tagName;
      if (index !== -1) {
        runName = runWithTagName.substring(0, index);
        tagName = runWithTagName.substring(index + 1);
      } else {
        tagName = runWithTagName;
      }

      return { runName, tagName };
    },

    async getTagIds(runWithTagName) {
      const tags = await this.getTags(null, runWithTagName);
      return tags.map(t => t.id.toNumber());
    },

    async getTags(tagIds, runWithTagName) {
      let runIds = null;
      let tagNames = null;

      if (runWithTagName) {
        const { runName, tagName } =
          this.extractTagWithRunName(runWithTagName);
        runIds = runName ? await this.getRunIds(runName) : null;
        tagNames = [ tagName ];
      }

      const limit = null;
      const offset = 0;
      const runHistoryFilter = new RunHistoryFilter({ tagIds, tagNames });

      return new Promise(resolve => {
        ccService.getClient().getRunHistory(runIds, limit, offset,
          runHistoryFilter, handleThriftError(res => {
            resolve(res);
          }));
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.v-tab {
  &.tags:not(.v-tab--disabled) {
    font-weight: bold;
  }

  &.v-tab--active:not(:focus)::before {
    opacity: 0.15;
  }
}
</style>
