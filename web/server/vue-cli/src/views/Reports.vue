<template>
  <splitpanes class="default-theme">
    <pane size="20" :style="{ 'min-width': '300px' }">
      <report-filter
        ref="reportFilter"
        v-fill-height
        :namespace="namespace"
        :report-count="totalItems"
        @refresh="refresh"
      />
    </pane>
    <pane>
      <checker-documentation-dialog
        :value.sync="checkerDocDialog"
        :checker="selectedChecker"
      />

      <v-btn
        color="primary"
        outlined
        small
        @click="viewMode = viewMode === 'tree' ? 'table' : 'tree'"
      >
        {{ viewMode === "table" ? "Tree view" : "Table view" }}
      </v-btn>

      <v-data-table
        v-if="viewMode === 'table'"
        v-model="selected"
        v-fill-height
        :headers="tableHeaders"
        :items="formattedReports"
        :options.sync="pagination"
        :loading="loading"
        loading-text="Loading reports..."
        :server-items-length.sync="totalItems"
        :footer-props="footerProps"
        :must-sort="true"
        :expanded.sync="expanded"
        show-expand
        show-select
        :mobile-breakpoint="1100"
        item-key="$id"
        @item-expanded="itemExpanded"
      >
        <template v-slot:top>
          <v-toolbar flat class="report-filter-toolbar" dense>
            <v-row>
              <v-col class="pa-0" align="right">
                <set-cleanup-plan-btn :value="selected" />
              </v-col>
            </v-row>
          </v-toolbar>
        </template>

        <template v-slot:expanded-item="{ item }">
          <td
            class="pa-0"
            :colspan="headers.length"
          >
            <v-list v-if="item.sameReports">
              <v-list-item
                v-for="report in item.sameReports"
                :key="report.reportId.toNumber()"
                dense
              >
                <v-list-item-content>
                  <v-list-item-title>
                    Same report in <kbd>{{ report.$runName }}</kbd> run:
                    <span>
                      <detection-status-icon
                        :status="parseInt(report.detectionStatus)"
                        :title="report.$detectionStatusTitle"
                        :size="18"
                      />
                      <review-status-icon
                        :status="parseInt(report.reviewData.status)"
                        :size="18"
                      />
                      <router-link
                        :to="{ name: 'report-detail', query: {
                          ...$router.currentRoute.query,
                          'report-id': report.reportId,
                          'report-hash': undefined
                        }}"
                      >
                        {{ report.checkedFile }}:{{ report.line }}
                      </router-link>
                    </span>
                  </v-list-item-title>
                </v-list-item-content>
              </v-list-item>
            </v-list>

            <v-card
              v-else
              flat
              tile
            >
              <v-card-text>
                Loading...
                <v-progress-linear
                  indeterminate
                  class="mb-0"
                />
              </v-card-text>
            </v-card>
          </td>
        </template>

        <template #item.bugHash="{ item }">
          <span :title="item.bugHash">
            {{ item.bugHash | truncate(10) }}
          </span>
        </template>

        <template #item.checkedFile="{ item }">
          <router-link
            :to="{ name: 'report-detail', query: {
              ...$router.currentRoute.query,
              'report-id': item.reportId ? item.reportId : undefined,
              'report-hash': item.bugHash,
              'report-filepath': reportFilter.isUnique
                ? `*${item.checkedFile}` : item.checkedFile
            }}"
            class="file-name"
          >
            {{ item.checkedFile }}
            <span v-if="item.line">@&nbsp;Line&nbsp;{{ item.line }}</span>
          </router-link>
        </template>

        <template #item.checkerId="{ item }">
          <span
            class="checker-name primary--text"
            @click="openCheckerDocDialog(item.checkerId, item.analyzerName)"
          >
            {{ item.checkerId }}
          </span>
        </template>

        <template #item.checkerMsg="{ item }">
          <span class="checker-message">
            {{ item.checkerMsg }}
          </span>
        </template>

        <template #item.severity="{ item }">
          <severity-icon :status="item.severity" />
        </template>

        <template #item.bugPathLength="{ item }">
          <v-chip :color="getBugPathLenColor(item.bugPathLength)">
            {{ item.bugPathLength }}
          </v-chip>
        </template>

        <template v-if="reportFilter.isUnique" #item.reviewData="{ item }">
          <review-status-icon
            v-for="status in sameReports[item.bugHash]"
            :key="status"
            :status="parseInt(status)"
            class="pa-1"
          />
        </template>
        <template v-else #item.reviewData="{ item }">
          <review-status-icon :status="parseInt(item.reviewData.status)" />
        </template>

        <template #item.detectionStatus="{ item }">
          <detection-status-icon
            :status="parseInt(item.detectionStatus)"
            :title="item.$detectionStatusTitle"
          />
        </template>
      </v-data-table>

      <splitpanes v-else class="default-theme tree-split">
        <pane
          size="30"
          :style="{ 'min-width': '250px', 'padding-top': '48px' }"
        >
          <v-treeview
            v-model="treeSelection"
            :items="treeItems"
            item-key="fullPath"
            open-on-click
            activatable
            selectable
            selection-type="independent"
            dense
            @update:active="onTreeFileClick"
            @input="onTreeSelectionChange"
          >
            <template #prepend="{ item, open }">
              <v-icon v-if="item.children.length > 0">
                {{ open ? 'mdi-folder-open' : 'mdi-folder' }}
              </v-icon>
              <v-icon v-else>
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
              <severity-icon
                v-for="sev in item.severities"
                :key="sev.id"
                :status="sev.id"
                :size="14"
                class="ml-1"
              />
              <v-chip class="right ml-2" small>
                {{ item.findings }}
              </v-chip>
            </template>
          </v-treeview>
        </pane>
        <pane>
          <v-data-table
            v-if="treeSelectedFile"
            :headers="treeTableHeaders"
            :items="formattedTreeReports"
            :loading="treeReportsLoading"
            loading-text="Loading reports..."
            :must-sort="false"
            dense
            :mobile-breakpoint="1100"
            item-key="$id"
            hide-default-footer
            :items-per-page="10"
          >
            <template #item.checkedFile="{ item }">
              <router-link
                :to="{ name: 'report-detail', query: {
                  ...$router.currentRoute.query,
                  'report-id': item.reportId ? item.reportId : undefined,
                  'report-hash': item.bugHash,
                  'report-filepath': item.checkedFile
                }}"
                class="file-name"
              >
                Line&nbsp;{{ item.line }}
              </router-link>
            </template>

            <template #item.checkerMsg="{ item }">
              <span class="checker-message">
                {{ item.checkerMsg }}
              </span>
            </template>

            <template #item.checkerId="{ item }">
              <span
                class="checker-name primary--text"
                @click="openCheckerDocDialog(
                  item.checkerId, item.analyzerName)"
              >
                {{ item.checkerId }}
              </span>
            </template>

            <template #item.severity="{ item }">
              <severity-icon :status="item.severity" />
            </template>

            <template #item.bugPathLength="{ item }">
              <v-chip :color="getBugPathLenColor(item.bugPathLength)">
                {{ item.bugPathLength }}
              </v-chip>
            </template>

            <template #item.reviewData="{ item }">
              <review-status-icon
                :status="parseInt(item.reviewData.status)"
              />
            </template>

            <template #item.detectionStatus="{ item }">
              <detection-status-icon
                :status="parseInt(item.detectionStatus)"
                :title="item.$detectionStatusTitle"
              />
            </template>
          </v-data-table>

          <v-container
            v-else
            class="text-center grey--text"
            fill-height
          >
            <v-row align="center" justify="center">
              <v-col>
                <v-icon large class="mb-2">
                  mdi-cursor-default-click
                </v-icon>
                <div>Select a file from the tree to view its reports</div>
              </v-col>
            </v-row>
          </v-container>
        </pane>
      </splitpanes>
    </pane>
  </splitpanes>
</template>

<script>
import { Pane, Splitpanes } from "splitpanes";

import { mapGetters, mapMutations } from "vuex";

import { ccService, handleThriftError } from "@cc-api";
import {
  Checker,
  MAX_QUERY_SIZE,
  Order,
  Severity,
  SortMode,
  SortType,
  ReportFilter as ThriftReportFilter
} from "@cc/report-server-types";
import { SET_REPORT_FILTER } from "@/store/mutations.type";

import { FillHeight } from "@/directives";
import { BugPathLengthColorMixin, DetectionStatusMixin } from "@/mixins";
import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";

import CheckerDocumentationDialog from
  "@/components/CheckerDocumentationDialog";
import { ReportFilter } from "@/components/Report/ReportFilter";
import { SetCleanupPlanBtn } from "@/components/Report/CleanupPlan";

const namespace = "report";

export default {
  name: "Reports",
  components: {
    CheckerDocumentationDialog,
    Splitpanes,
    Pane,
    DetectionStatusIcon,
    ReviewStatusIcon,
    SeverityIcon,
    ReportFilter,
    SetCleanupPlanBtn
  },
  directives: { FillHeight },
  mixins: [ BugPathLengthColorMixin, DetectionStatusMixin ],

  data() {
    const itemsPerPageOptions = [ 25, 50, 100 ];

    const page = parseInt(this.$router.currentRoute.query["page"]) || 1;
    const itemsPerPage =
      parseInt(this.$router.currentRoute.query["items-per-page"]) ||
      itemsPerPageOptions[0];
    const sortBy = this.$router.currentRoute.query["sort-by"];
    const sortDesc = this.$router.currentRoute.query["sort-desc"];

    return {
      viewMode: "table",
      headers: [
        {
          text: "",
          value: "data-table-expand"
        },
        {
          text: "Report hash",
          value: "bugHash",
          sortable: false
        },
        {
          text: "File",
          value: "checkedFile",
          sortable: true
        },
        {
          text: "Message",
          value: "checkerMsg",
          sortable: false
        },
        {
          text: "Checker name",
          value: "checkerId",
          sortable: true
        },
        {
          text: "Analyzer",
          value: "analyzerName",
          align: "center",
          sortable: false
        },
        {
          text: "Severity",
          value: "severity",
          sortable: true
        },
        {
          text: "Bug path length",
          value: "bugPathLength",
          align: "center",
          sortable: true
        },
        {
          text: "Latest review status",
          value: "reviewData",
          align: "center",
          sortable: true
        },
        {
          text: "Latest detection status",
          value: "detectionStatus",
          align: "center",
          sortable: true
        },
        {
          text: "Timestamp",
          value: "timestamp",
          align: "center",
          sortable: true
        },
        {
          text: "Chronological order",
          value: "chronological_order",
          align: "center",
          sortable: true
        },
        {
          text: "Testcase",
          value: "testcase",
          align: "center",
          sortable: true
        }
      ],
      reports: [],
      allReportsFileCounts: [],
      sameReports: {},
      hasTimeStamp: true,
      hasTestCase : true,
      hasChronologicalOrder: true,
      selected: [],
      namespace: namespace,
      pagination: {
        page: page,
        itemsPerPage: itemsPerPage,
        sortBy: sortBy ? [ sortBy ] : [],
        sortDesc: sortDesc !== undefined ? [ !!sortDesc ] : []
      },
      footerProps: {
        itemsPerPageOptions: itemsPerPageOptions
      },
      totalItems: 0,
      loading: false,
      runIdsUnwatch: null,
      reportFilterUnwatch: null,
      cmpDataUnwatch: null,
      initalized: false,
      checkerDocDialog: false,
      selectedChecker: null,
      expanded: [],
      treeItems: [],
      treeSelectedFile: null,
      treeReports: [],
      treeReportsLoading: false,
      fileSeverities: {},
      treeSelection: []
    };
  },

  computed: {
    ...mapGetters(namespace, {
      runIds: "getRunIds",
      reportFilter: "getReportFilter",
      cmpData: "getCmpData"
    }),

    tableHeaders() {
      if (!this.headers) return;

      return this.headers.filter(header => {
        if (header.value === "detectionStatus") {
          return !this.reportFilter.isUnique;
        }

        if (header.value === "data-table-expand") {
          return this.reportFilter.isUnique;
        }

        if (header.value === "timestamp") {
          return this.hasTimeStamp &&
            !this.reportFilter.isUnique;
        }

        if (header.value === "testcase") {
          return this.hasTestCase &&
            !this.reportFilter.isUnique;
        }

        if (header.value === "chronological_order") {
          return this.hasChronologicalOrder &&
            !this.reportFilter.isUnique;
        }

        return true;
      });
    },

    formattedReports() {
      return this.reports.map(report => {
        const reportId = report.reportId ? report.reportId.toString() : "";
        const id = reportId + report.bugHash;

        const detectionStatus =
          this.detectionStatusFromCodeToString(report.detectionStatus);
        const detectedAt = report.detectedAt
          ? this.$options.filters.prettifyDate(report.detectedAt) : null;
        const fixedAt = report.fixedAt
          ? this.$options.filters.prettifyDate(report.fixedAt) : null;

        const detectionStatusTitle = [
          `Status: ${detectionStatus}`,
          ...(detectedAt ? [ `Detected at: ${detectedAt}` ] : []),
          ...(fixedAt ? [ `Fixed at: ${fixedAt}` ] : [])
        ].join("\n");

        return {
          ...report,
          "$detectionStatusTitle": detectionStatusTitle,
          "$id": id,
          "sameReports": report.sameReports,
          "timestamp": report.annotations["timestamp"],
          "testcase": report.annotations["testcase"],
          "chronological_order": report.annotations["chronological_order"]
        };
      });
    },

    treeTableHeaders() {
      return [
        {
          text: "Line",
          value: "checkedFile",
          sortable: false
        },
        {
          text: "Message",
          value: "checkerMsg",
          sortable: false
        },
        {
          text: "Checker name",
          value: "checkerId",
          sortable: false
        },
        {
          text: "Analyzer",
          value: "analyzerName",
          align: "center",
          sortable: false
        },
        {
          text: "Severity",
          value: "severity",
          sortable: false
        },
        {
          text: "Bug path length",
          value: "bugPathLength",
          align: "center",
          sortable: false
        },
        {
          text: "Latest review status",
          value: "reviewData",
          align: "center",
          sortable: false
        },
        {
          text: "Latest detection status",
          value: "detectionStatus",
          align: "center",
          sortable: false
        }
      ];
    },

    formattedTreeReports() {
      return this.treeReports.map((report, idx) => {
        const detectionStatus =
          this.detectionStatusFromCodeToString(report.detectionStatus);
        const detectedAt = report.detectedAt
          ? this.$options.filters.prettifyDate(report.detectedAt) : null;
        const fixedAt = report.fixedAt
          ? this.$options.filters.prettifyDate(report.fixedAt) : null;

        const detectionStatusTitle = [
          `Status: ${detectionStatus}`,
          ...(detectedAt ? [ `Detected at: ${detectedAt}` ] : []),
          ...(fixedAt ? [ `Fixed at: ${fixedAt}` ] : [])
        ].join("\n");

        const reportId = report.reportId
          ? report.reportId.toString() : String(idx);

        return {
          ...report,
          "$detectionStatusTitle": detectionStatusTitle,
          "$id": reportId + report.bugHash
        };
      });
    },

  },

  watch: {
    pagination: {
      handler() {
        this.updateUrl();
        if (this.initalized) {
          this.fetchReports();
        }
      },
      deep: true
    },
    formattedReports: {
      handler() {
        this.hasTimeStamp =
          this.formattedReports.some(report => report.timestamp);

        this.hasTestCase =
          this.formattedReports.some(report => report.testcase);

        this.hasChronologicalOrder =
          this.formattedReports.some(report => report["chronological_order"]);
      }
    },
    allReportsFileCounts: {
      handler() {
        this.buildTreeItems();
        this.fetchFileSeverities();
      },
      deep: true
    }
  },

  methods: {
    ...mapMutations(namespace, {
      setReportFilter: SET_REPORT_FILTER
    }),

    buildTreeItems() {
      const items = [];

      Object.entries(
        this.allReportsFileCounts || {}
      ).forEach(([ filePath, count ]) => {
        if (!filePath) return;
        const pathParts = filePath.split("/").slice(0, -1);
        let currentLevel = items;
        let currentPath = "";
        pathParts.forEach(part => {
          if (part === "") return;

          currentPath += "/" + part;
          let existingPart = currentLevel.find(
            item => item.name === part
          );
          if (!existingPart) {
            existingPart = {
              name: part,
              fullPath: currentPath,
              children: [],
              findings: 0,
              severities: []
            };
            currentLevel.push(existingPart);
          }
          currentLevel = existingPart.children;
        });

        // append filename as a child of the last directory
        const fileName = filePath.split("/").slice(-1)[0];
        const sevs = this.fileSeverities[filePath] || [];
        if (fileName) {
          const existingFile = currentLevel.find(
            item => item.name === fileName
          );
          if (existingFile) {
            existingFile.findings += count;
            existingFile.severities = sevs;
          } else {
            currentLevel.push({
              name: fileName,
              fullPath: filePath,
              children: [],
              findings: count,
              severities: sevs
            });
          }
        }
      });

      // count findings for directories
      // try replacing with getCheckerCounts if performance is an issue
      function countFindings(node) {
        if (node.children.length === 0) {
          return node.findings;
        } else {
          node.findings = node.children.reduce((sum, child) => {
            return sum + countFindings(child);
          }, 0);
          const sevMap = {};
          node.children.forEach(child => {
            (child.severities || []).forEach(s => {
              if (!sevMap[s.id]) {
                sevMap[s.id] = { id: s.id, count: 0 };
              }
              sevMap[s.id].count += s.count;
            });
          });
          node.severities = Object.values(sevMap)
            .sort((a, b) => b.id - a.id);
          return node.findings;
        }
      }
      items.forEach(countFindings);
      this.treeItems = items;
    },

    onTreeFileClick(activeItems) {
      if (!activeItems || activeItems.length === 0) {
        this.treeSelectedFile = null;
        this.treeReports = [];
        return;
      }

      const fullPath = activeItems[0];
      if (!fullPath) return;

      const isDir = this.isDirectory(fullPath);
      const filterPath = isDir ? fullPath + "/*" : fullPath;

      this.treeSelectedFile = fullPath;
      this.treeReportsLoading = true;

      const filter = new ThriftReportFilter(this.reportFilter);
      filter.filepath = [ filterPath ];

      ccService.getClient().getRunResults(
        this.runIds, MAX_QUERY_SIZE, 0, [],
        filter, this.cmpData, false,
        handleThriftError(reports => {
          this.treeReports = reports;
          this.treeReportsLoading = false;
        })
      );
    },

    itemExpanded(expandedItem) {
      if (expandedItem.item.sameReports) return;

      const bugHash = expandedItem.item.bugHash;
      ccService.getSameReports(bugHash).then(sameReports => {
        expandedItem.item.sameReports = sameReports;
      });
    },

    onTreeSelectionChange(selectedPaths) {
      if (!selectedPaths || !selectedPaths.length) {
        this.treeSelectedFile = null;
        this.treeReports = [];
        return;
      }

      const paths = selectedPaths.map(fp => {
        const isDir = this.isDirectory(fp);
        return isDir ? fp + "/*" : fp;
      });

      this.treeSelectedFile = selectedPaths.join(", ");
      this.treeReportsLoading = true;

      const filter = new ThriftReportFilter(this.reportFilter);
      filter.filepath = paths;

      ccService.getClient().getRunResults(
        this.runIds, MAX_QUERY_SIZE, 0, [],
        filter, this.cmpData, false,
        handleThriftError(reports => {
          this.treeReports = reports;
          this.treeReportsLoading = false;
        })
      );
    },

    toggleTreeItem(item) {
      const idx = this.treeSelection.indexOf(
        item.fullPath
      );
      if (idx === -1) {
        this.treeSelection =
          [ ...this.treeSelection, item.fullPath ];
      } else {
        this.treeSelection =
          this.treeSelection.filter(
            p => p !== item.fullPath
          );
      }
      this.onTreeSelectionChange(this.treeSelection);
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

    fetchFileSeverities() {
      const files = Object.keys(
        this.allReportsFileCounts || {}
      );
      if (!files.length) return;

      const sevMap = {};
      let pending = files.length;

      files.forEach(filePath => {
        const filter = new ThriftReportFilter(
          this.reportFilter
        );
        filter.filepath = [ filePath ];
        filter.severity = null;

        ccService.getClient().getSeverityCounts(
          this.runIds, filter, this.cmpData,
          handleThriftError(res => {
            const sevs = [];
            Object.keys(Severity).forEach(s => {
              const id = Severity[s];
              const cnt = res[id];
              if (cnt) {
                const n = cnt.toNumber
                  ? cnt.toNumber() : cnt;
                if (n > 0) {
                  sevs.push({ id: id, count: n });
                }
              }
            });
            sevs.sort((a, b) => b.id - a.id);
            sevMap[filePath] = sevs;

            pending--;
            if (pending === 0) {
              this.fileSeverities =
                Object.assign({}, sevMap);
              this.buildTreeItems();
            }
          }));
      });
    },

    loadFileCounts() {
      ccService.getClient().getFileCounts(
        this.runIds, this.reportFilter,
        this.cmpData, 0, 0,
        handleThriftError(fileCounts => {
          this.allReportsFileCounts =
            fileCounts || [];
        }));
    },

    getSortMode() {
      let type = null;
      switch (this.pagination.sortBy[0]) {
      case "checkedFile":
        type = SortType.FILENAME;
        break;
      case "checkerId":
        type = SortType.CHECKER_NAME;
        break;
      case "detectionStatus":
        type = SortType.DETECTION_STATUS;
        break;
      case "reviewData":
        type = SortType.REVIEW_STATUS;
        break;
      case "bugPathLength":
        type = SortType.BUG_PATH_LENGTH;
        break;
      case "timestamp":
        type = SortType.TIMESTAMP;
        break;
      case "testcase":
        type = SortType.TESTCASE;
        break;
      case "chronological_order":
        type = SortType.CHRONOLOGICAL_ORDER;
        break;
      default:
        type = SortType.SEVERITY;
      }

      const ord = this.pagination.sortDesc[0] ? Order.DESC : Order.ASC;

      return [ new SortMode({ type: type, ord: ord }) ];
    },

    openCheckerDocDialog(checkerId, analyzerName) {
      this.selectedChecker = new Checker({
        checkerId: checkerId,
        analyzerName: analyzerName
      });
      this.checkerDocDialog = true;
    },

    updateUrl() {
      const defaultItemsPerPage = this.footerProps.itemsPerPageOptions[0];
      const itemsPerPage =
        this.pagination.itemsPerPage === defaultItemsPerPage
          ? undefined
          : this.pagination.itemsPerPage;

      const page = this.pagination.page === 1
        ? undefined : this.pagination.page;
      const sortBy = this.pagination.sortBy.length
        ? this.pagination.sortBy[0] : undefined;
      const sortDesc = this.pagination.sortDesc.length
        ? this.pagination.sortDesc[0] : undefined;

      this.$router.replace({
        query: {
          ...this.$route.query,
          "items-per-page": itemsPerPage,
          "page": page,
          "sort-by": sortBy,
          "sort-desc": sortDesc,
        }
      }).catch(() => {});
    },

    refresh() {
      this.expanded = [];

      ccService.getClient().getRunResultCount(this.runIds,
        this.reportFilter, this.cmpData, handleThriftError(res => {
          this.totalItems = res.toNumber();
        }));

      if (this.pagination.page !== 1 && this.initalized) {
        this.pagination.page = 1;
      } else {
        this.fetchReports();
      }
    },

    fetchReports() {
      this.loading = true;

      const limit = this.pagination.itemsPerPage;
      const offset = limit * (this.pagination.page - 1);
      const sortType = this.getSortMode();
      const getDetails = false;

      ccService.getClient().getRunResults(this.runIds, limit, offset, sortType,
        this.reportFilter, this.cmpData, getDetails,
        handleThriftError(reports => {
          this.reports = reports;
          this.loading = false;
          this.initalized = true;

          reports.forEach(report => {
            ccService.getSameReports(report.bugHash).then(sameReports => {
              this.$set(
                this.sameReports, report.bugHash,
                [ ...new Set(sameReports.map(r => r.reviewData.status)) ]);
            });
          });
        }));

      ccService.getClient().getFileCounts(
        this.runIds, this.reportFilter,
        this.cmpData, 0, 0,
        handleThriftError(fileCounts => {
          this.allReportsFileCounts =
            fileCounts;
        }));

    }


  }
};
</script>

<style lang="scss" scoped>
.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}

.v-data-table {
  .file-name,
  .checker-name,
  .checker-message {
    word-break: break-word;
  }

  .checker-name {
    cursor: pointer;
  }
}

.tree-split {
  .splitpanes__pane {
    background-color: inherit;
  }
}

.tree-item-label {
  font-size: 0.85em;
}
</style>
