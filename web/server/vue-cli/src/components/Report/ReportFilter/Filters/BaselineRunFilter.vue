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
    :panel="panel"
    @cancel="cancelRunSelection"
    @select="prevSelectedRuns = $event"
    @clear="clear(true)"
    @on-menu-show="selectTagForRun = null"
  >
    <template v-slot:append-toolbar-title>
      <selected-toolbar-title-items
        v-if="selectedToolbarTitleItems.length"
        :value="selectedToolbarTitleItems"
      />
    </template>

    <template
      v-slot:menu-content="{
        items,
        prevSelectedItems,
        cancel: cancelItemSelection,
        select,
        onApplyFinished
      }"
    >
      <v-menu
        v-model="selectTagMenu"
        content-class="select-tag-menu"
        :close-on-content-click="false"
        :nudge-width="300"
        :max-width="550"
        offset-x
      >
        <template v-slot:activator="{ on: menu }">
          <items
            :items="items"
            :selected-items="prevSelectedItems"
            :search="search"
            :limit="defaultLimit"
            :format="formatRunTitle"
            @apply="apply"
            @apply:finished="onApplyFinished"
            @cancel="cancelItemSelection"
            @select="select"
            @update:items="items.splice(0, items.length, ...$event)"
          >
            <template v-slot:append-toolbar>
              <bulb-message>
                Use the <v-icon>mdi-cog</v-icon> button beside each run after
                hovering on the run to specify a tag.
              </bulb-message>
            </template>

            <template v-slot:prepend-count="{ hover, item }">
              <v-tooltip
                v-if="hover || selectTagForRun === item"
                max-width="200"
                right
              >
                <template v-slot:activator="{ on: tooltip }">
                  <v-btn
                    icon
                    small
                    v-on="{ ...tooltip, ...menu }"
                    @click.stop="specifyTag(item)"
                  >
                    <v-icon>mdi-cog</v-icon>
                  </v-btn>
                </template>

                <span>
                  Specify a run tag for this run to filter reports that
                  were <i>DETECTED</i> and <i>NOT FIXED BEFORE</i> the date
                  when the selected tag was created.
                </span>
              </v-tooltip>
            </template>

            <template v-slot:title="{ item }">
              <v-list-item-title :title="item.title">
                {{ item.title }}
              </v-list-item-title>
            </template>

            <template v-slot:icon>
              <v-icon color="grey">
                mdi-play-circle
              </v-icon>
            </template>
          </items>
        </template>

        <v-card v-if="selectTagForRun" flat>
          <baseline-tag-items
            :namespace="namespace"
            :selected-items="prevSelectedTagItems"
            :run-id="selectTagForRun.runIds[0]"
            :limit="defaultLimit"
            @apply="applyTagSelection"
            @cancel="cancelTagSelection"
            @select="selectRunTags"
          >
            <template v-slot:icon>
              <v-icon color="grey">
                mdi-tag
              </v-icon>
            </template>
          </baseline-tag-items>
        </v-card>
      </v-menu>
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
          <v-list-item-title :title="titles[item.id]">
            {{ titles[item.id] }}
          </v-list-item-title>
        </template>
      </items-selected>
    </template>
  </select-option>
</template>

<script>
import _ from "lodash";

import { ccService, extractTagWithRunName, handleThriftError } from "@cc-api";
import { ReportFilter } from "@cc/report-server-types";

import BulbMessage from "@/components/BulbMessage";
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
    BulbMessage,
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
      selectTagMenu: false,
      selectTagForRun: null,
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
      return this.selectedItems.reduce((acc, curr) => ({
        ...acc,
        [curr.id]: this.getSelectedRunTitle(curr).title
      }), {});
    },

    selectedToolbarTitleItems() {
      return this.selectedItems.map(item => ({
        title: this.titles[item.id]
      }));
    }
  },

  methods: {
    formatRunItemWithTags(run, tags) {
      const tagNames = tags
        .filter(s => run.runIds.includes(s.runId))
        .map(s => s.tagName);

      run.title = tagNames.length
        ? `${run.id}:${tagNames.join(", ")}`
        : run.id;

      return run;
    },

    formatRunTitle(run) {
      return this.formatRunItemWithTags(run, this.prevSelectedTagItems);
    },

    getSelectedRunTitle(run) {
      return this.formatRunItemWithTags(run, this.selectedTagItems);
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
        runIds: await ccService.getRunIds(s),
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
        ? (await ccService.getTags(null, tagIds)).map(t => {
          const time = this.$options.filters.prettifyDate(t.time);
          return {
            id: t.id.toNumber(),
            runName: t.runName,
            runId: t.runId.toNumber(),
            tagName : t.versionTag || time,
            time: time,
            title: t.versionTag,
            count: "N/A"
          };
        })
        : [];

      // Get tags by tag names (backward compatibility).
      const tags2 = tagWithRunNames.length
        ? (await Promise.all(tagWithRunNames.map(async s => {
          const { runName, tagName } = extractTagWithRunName(s);
          const runIds = runName ? await ccService.getRunIds(runName) : null;
          const tags = await ccService.getTags(runIds, null, [ tagName ]);
          return {
            id: tags[0].id,
            runName: runName ? runName : tags[0].runName,
            runId: tags[0].runId.toNumber(),
            time: tags[0].time,
            tagName,
            title: s,
            count: "N/A"
          };
        })))
        : [];

      return tags1.concat(tags2);
    },

    async initByUrl() {
      let runs = [].concat(this.$route.query[this.id] || []);
      const tags = [].concat(this.$route.query[this.runTagId] || []);

      if (runs.length || tags.length) {
        let selectedTags = [];
        if (tags.length) {
          selectedTags = await this.getSelectedTagItems(tags);

          // Add runs related to tags.
          runs.push(...selectedTags.map(t => t.runName));

          // Filter out duplicates.
          runs = [ ...new Set(runs) ];
        }

        const selectedRuns = await this.getSelectedRunItems(runs);

        await this.setSelectedItems(selectedRuns, selectedTags, false);
      }
    },

    cancelTagSelection() {
      this.prevSelectedTagItems = _.cloneDeep(this.selectedTagItems);
      this.selectTagMenu = false;
      this.selectTagForRun = null;
    },

    cancelRunSelection() {
      this.prevSelectedRuns = _.cloneDeep(this.selectedItems);
      this.cancelTagSelection();
    },

    apply(selectedRunItems) {
      if (!this.runFilterIsChanged() && !this.tagFilterIsChanged()) return;

      this.setSelectedItems(selectedRunItems, this.prevSelectedTagItems);
    },

    applyTagSelection() {
      this.selectTagMenu = false;
      this.prevSelectedTagItems.forEach(t => {
        this.bus.$emit("select", item => item.runIds.includes(t.runId));
      });
    },

    async clear(updateUrl) {
      await this.setSelectedItems([], [], updateUrl);
    },

    selectRunTags(selectedItems) {
      this.prevSelectedTagItems = _.cloneDeep(selectedItems);
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
            item.runIds = await ccService.getRunIds(item.title);
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

    specifyTag(run) {
      if (this.selectTagForRun === run) {
        this.selectTagForRun = null;
        return;
      }

      this.selectTagForRun = run;
      setTimeout(() => this.selectTagMenu = true, 0);
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
