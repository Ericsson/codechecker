<template>
  <select-option
    :id="id"
    title="File path"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :loading="loading"
    :limit="defaultLimit"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:menu-content="{ onApplyFinished }">
      <v-card flat>
        <v-toolbar class="pa-2" dense flat>
          <v-text-field
            v-model="treeFilter"
            hide-details
            prepend-icon="mdi-magnify"
            single-line
            label="Search for files (e.g.: */src/*)..."
            clearable
          />
        </v-toolbar>

        <AnywhereOnReportPath v-model="isAnywhere" />

        <v-divider v-if="treeItems.length > 0" class="my-1" />

        <v-treeview
          v-if="treeItems.length > 0"
          v-model="treeSelection"
          :items="treeItems"
          selectable
          selection-type="independent"
          item-key="fullPath"
          open-on-click
          dense
          class="file-path-tree"
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
            <span
              class="tree-item-label"
              @click.stop="toggleTreeItem(item)"
            >
              {{ item.name }}
            </span>
            <v-chip class="ml-2" x-small>
              {{ item.findings }}
            </v-chip>
          </template>
        </v-treeview>

        <v-card-actions>
          <v-spacer />

          <v-btn
            text
            class="clear-all-btn"
            color="grey"
            @click="clearAll(onApplyFinished)"
          >
            <v-icon left>
              mdi-close-circle-outline
            </v-icon>
            Clear All
          </v-btn>

          <v-btn
            text
            class="apply-btn"
            color="primary"
            :disabled="treeSelection.length === 0"
            @click="applyTreeSelection(onApplyFinished)"
          >
            <v-icon left>
              mdi-check-circle-outline
            </v-icon>
            Apply
          </v-btn>
        </v-card-actions>
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
      isAnywhere: false,
      allFileCounts: {},
      treeSelection: [],
      treeFilter: ""
    };
  },

  computed: {
    filteredFileCounts() {
      if (!this.treeFilter) return this.allFileCounts;

      const pattern = this.treeFilter
        .replace(/[.+^${}()|[\]\\]/g, "\\$&")
        .replace(/\*/g, ".*")
        .replace(/\?/g, ".");
      const regex = new RegExp(pattern, "i");
      const filtered = {};
      Object.entries(this.allFileCounts || {}).forEach(([ fp, count ]) => {
        if (regex.test(fp)) {
          filtered[fp] = count;
        }
      });
      return filtered;
    },

    treeItems() {
      const items = [];

      Object.entries(
        this.filteredFileCounts || {}
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
      await this.fetchAllFileCounts();

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
      const allCounts = {};

      return new Promise(resolve => {
        const fetchPage = offset => {
          ccService.getClient().getFileCounts(
            this.runIds, reportFilter,
            this.cmpData, 500, offset,
            handleThriftError(res => {
              const keys = Object.keys(res || {});
              keys.forEach(fp => {
                allCounts[fp] = res[fp];
              });
              if (keys.length >= 500) {
                fetchPage(offset + 500);
              } else {
                this.allFileCounts = Object.assign({}, allCounts);
                resolve();
              }
            }));
        };
        fetchPage(0);
      });
    },

    clearAll(onApplyFinished) {
      this.treeSelection = [];
      this.clear(true);
      if (onApplyFinished) onApplyFinished();
    },

    applyTreeSelection(onApplyFinished) {
      if (!this.treeSelection.length) return;

      const items = this.treeSelection.map(fp => {
        const isDir = this.isDirectory(fp);
        const filterId = isDir ? fp + "/*" : fp;
        return {
          id: filterId,
          title: filterId,
          count: "N/A"
        };
      });
      this.setSelectedItems(items);
      if (onApplyFinished) onApplyFinished();
    },

    isDirectory(fullPath) {
      const find = nodes => {
        for (const n of nodes) {
          if (n.fullPath === fullPath) {
            return n.children.length > 0;
          }
          if (n.children.length) {
            const r = find(n.children);
            if (r !== null) return r;
          }
        }
        return null;
      };
      return !!find(this.treeItems);
    },

    toggleTreeItem(item) {
      const idx = this.treeSelection.indexOf(item.fullPath);
      if (idx === -1) {
        this.treeSelection =
          [ ...this.treeSelection, item.fullPath ];
      } else {
        this.treeSelection = this.treeSelection.filter(
          p => p !== item.fullPath
        );
      }
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