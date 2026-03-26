<template>
  <select-option
    :id="id"
    ref="selectOption"
    title="File path"
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
    <template v-slot:menu-content>
      <v-card flat>
        <AnywhereOnReportPath v-model="isAnywhere" />

        <v-divider v-if="treeItems.length > 0" class="my-1" />

        <v-treeview
          v-if="treeItems.length > 0"
          :items="treeItems"
          activatable
          item-key="fullPath"
          open-on-click
          dense
          class="file-path-tree"
          @update:active="onTreeFileClick"
        >
          <template #prepend="{ item, open }">
            <v-icon v-if="item.children.length > 0" small>
              {{ open ? 'mdi-folder-open' : 'mdi-folder' }}
            </v-icon>
            <v-icon v-else small>
              mdi-file
            </v-icon>
          </template>
          <template #label="{ item }">
            <span class="tree-item-label">{{ item.name }}</span>
            <v-chip class="ml-2" x-small>
              {{ item.findings }}
            </v-chip>
          </template>
        </v-treeview>
      </v-card>
    </template>

    <template v-slot:icon>
      <v-icon color="grey">
        mdi-file-document-outline
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
import { ReportFilter } from "@cc/report-server-types";

import AnywhereOnReportPath from "./SelectOption/AnywhereOnReportPath.vue";
import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "FilePathFilter",
  components: {
    AnywhereOnReportPath,
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "filepath",
      anywhereId: "anywhere-filepath",
      search: {
        placeHolder: "Search for files (e.g.: */src/*)...",
        regexLabel: "Filter by wildcard pattern (e.g.: */src/*)",
        filterItems: this.filterItems
      },
      isAnywhere: false,
      allFileCounts: {}
    };
  },

  computed: {
    treeItems() {
      const items = [];

      Object.entries(
        this.allFileCounts || {}
      ).forEach(([ filePath, count ]) => {
        if (!filePath) return;
        const numCount = typeof count === "object" && count.toNumber
          ? count.toNumber() : count;
        const pathParts = filePath.split("/").slice(0, -1);
        let currentLevel = items;
        let currentPath = "";

        pathParts.forEach(part => {
          if (part === "") return;
          currentPath += "/" + part;
          let existingPart = currentLevel.find(item => item.name === part);
          if (!existingPart) {
            existingPart = {
              name: part,
              fullPath: currentPath,
              children: [],
              findings: 0
            };
            currentLevel.push(existingPart);
          }
          currentLevel = existingPart.children;
        });

        const fileName = filePath.split("/").slice(-1)[0];
        if (fileName) {
          const existingFile = currentLevel.find(
            item => item.name === fileName
          );
          if (existingFile) {
            existingFile.findings += numCount;
          } else {
            currentLevel.push({
              name: fileName,
              fullPath: filePath,
              children: [],
              findings: numCount
            });
          }
        }
      });

      function countFindings(node) {
        if (node.children.length === 0) return node.findings;
        node.findings = node.children.reduce(
          (sum, child) => sum + countFindings(child), 0
        );
        return node.findings;
      }
      items.forEach(countFindings);
      return items;
    }
  },

  watch: {
    isAnywhere() {
      this.updateReportFilter();
      this.$emit("update:url");
      this.update();
    }
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        filepath: this.selectedItems.map(item => item.id),
        fileMatchesAnyPoint: this.isAnywhere
      });
    },

    onReportFilterChange(key) {
      if (key === "filepath") {
        const paths =
          this.reportFilter.filepath || [];
        const curIds =
          this.selectedItems.map(i => i.id);
        const same =
          paths.length === curIds.length &&
          paths.every((p, i) => p === curIds[i]);

        if (!same) {
          this.selectedItems = paths.map(p => ({
            id: p,
            title: p,
            count: "N/A"
          }));
          this.panel = paths.length > 0;
        }
        return;
      }
      this.update();
    },

    getUrlState() {
      const state =
        this.selectedItems.map(item => this.encodeValue(item.id));

      return {
        [this.id]: state.length ? state : undefined,
        [this.anywhereId]: this.isAnywhere || undefined
      };
    },

    initByUrl() {
      this.isAnywhere = !!this.$route.query[this.anywhereId];
      this.initCheckOptionsByUrl();
    },

    async update() {
      this.bus.$emit("update");
      this.fetchAllFileCounts();

      if (!this.selectedItems.length) return;

      const items = await this.fetchItems({
        limit: this.selectedItems.length,
        query: this.selectedItems.map(item => item.id)
      });

      this.selectedItems.forEach(selectedItem => {
        const item = items.find(i => i.id === selectedItem.id);
        selectedItem.count = item ? item.count : null;
        selectedItem.value = item ? item.value : null;
      });
    },

    fetchAllFileCounts() {
      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.filepath = null;

      ccService.getClient().getFileCounts(
        this.runIds, reportFilter, this.cmpData, 0, 0,
        handleThriftError(res => {
          this.allFileCounts = res || {};
        }));
    },

    onTreeFileClick(activeItems) {
      if (!activeItems || activeItems.length === 0) return;
      const filePath = activeItems[0];
      if (!filePath) return;

      // Prevent the menu close from resetting the selection.
      this.$refs.selectOption.preventApply = true;
      this.$refs.selectOption.menu = false;

      this.setSelectedItems([
        { id: filePath, title: filePath, count: "N/A" }
      ]);
    },

    fetchItems(opt={}) {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.filepath = opt.query;

      const limit = opt.limit || this.defaultLimit;
      const offset = null;

      return new Promise(resolve => {
        ccService.getClient().getFileCounts(this.runIds, reportFilter,
          this.cmpData, limit, offset, handleThriftError(res => {
          // Order the results alphabetically.
            resolve(Object.keys(res).sort((a, b) => {
              if (a < b) return -1;
              if (a > b) return 1;
              return 0;
            }).map(file => {
              return {
                id : file,
                title: file,
                count: res[file]?.toNumber() || 0
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

.file-path-tree {
  max-height: 400px;
  overflow-y: auto;
}

.tree-item-label {
  font-size: 0.85em;
}
</style>