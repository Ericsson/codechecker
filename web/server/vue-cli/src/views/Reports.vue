<template>
  <splitpanes class="default-theme">
    <pane size="20" :style="{ 'min-width': '300px' }">
      <report-filter
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

      <v-btn-toggle
        v-model="viewMode"
        mandatory
        dense
        class="mb-2"
      >
        <v-btn
          value="table"
          small
          @click="setReportFilter({ filepath: null })"
        >
          Report List
        </v-btn>
        <v-btn
          value="tree"
          small
          @click="setReportFilter({ filepath: null })"
        >
          File Tree
        </v-btn>
      </v-btn-toggle>

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

      <div v-else class="tree-view-container" style="padding-top: 48px;">
        <div class="tree-header">
          <span class="tree-header-name">Name</span>
          <span class="tree-header-cell">All</span>
          <span class="tree-header-cell">
            <severity-icon :status="Severity.STYLE" :size="14" />
          </span>
          <span class="tree-header-cell">
            <severity-icon :status="Severity.LOW" :size="14" />
          </span>
          <span class="tree-header-cell">
            <severity-icon :status="Severity.MEDIUM" :size="14" />
          </span>
          <span class="tree-header-cell">
            <severity-icon :status="Severity.HIGH" :size="14" />
          </span>
          <span class="tree-header-cell">
            <severity-icon :status="Severity.CRITICAL" :size="14" />
          </span>
          <span class="tree-header-cell">
            <review-status-icon :status="0" :size="14" />
          </span>
          <span class="tree-header-cell">
            <review-status-icon :status="1" :size="14" />
          </span>
          <span class="tree-header-cell">
            <review-status-icon :status="2" :size="14" />
          </span>
          <span class="tree-header-cell">
            <review-status-icon :status="3" :size="14" />
          </span>
        </div>
        <v-treeview
          :items="treeItems"
          item-key="fullPath"
          open-on-click
          dense
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
            <div class="tree-row">
              <span
                class="tree-item-label clickable"
                @click.stop="onTreeItemClick(item)"
              >{{ item.name }}</span>
              <span class="tree-stat-cell">{{ item.findings }}</span>
              <span class="tree-stat-cell">
                {{ item.stats.style || '' }}
              </span>
              <span class="tree-stat-cell">
                {{ item.stats.low || '' }}
              </span>
              <span class="tree-stat-cell">
                {{ item.stats.medium || '' }}
              </span>
              <span class="tree-stat-cell">
                {{ item.stats.high || '' }}
              </span>
              <span class="tree-stat-cell">
                {{ item.stats.critical || '' }}
              </span>
              <span class="tree-stat-cell">
                {{ item.stats.unreviewed || '' }}
              </span>
              <span class="tree-stat-cell">
                {{ item.stats.confirmed || '' }}
              </span>
              <span class="tree-stat-cell">
                {{ item.stats.false_positive || '' }}
              </span>
              <span class="tree-stat-cell">
                {{ item.stats.intentional || '' }}
              </span>
            </div>
          </template>
        </v-treeview>
      </div>
    </pane>
  </splitpanes>
</template>

<script>
import { Pane, Splitpanes } from "splitpanes";

import { mapGetters, mapMutations } from "vuex";

import { ccService, handleThriftError } from "@cc-api";
import {
  Checker,
  Order,
  Severity,
  SortMode,
  SortType
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
      allReportsFileCounts: {},
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
      fileSeverities: {},
      Severity: Severity
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
      },
      deep: true
    }
  },

  methods: {
    ...mapMutations(namespace, {
      setReportFilter: SET_REPORT_FILTER
    }),

    onTreeItemClick(item) {
      const isDir = item.children && item.children.length > 0;
      const pattern = isDir ? item.fullPath + "/*" : item.fullPath;
      this.setReportFilter({ filepath: [ pattern ] });
      this.viewMode = "table";
    },

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
              stats: {}
            };
            currentLevel.push(existingPart);
          }
          currentLevel = existingPart.children;
        });

        // append filename as a child of the last directory
        const fileName = filePath.split("/").slice(-1)[0];
        const fileStats = this.fileSeverities[filePath] || {};
        if (fileName) {
          const existingFile = currentLevel.find(
            item => item.name === fileName
          );
          if (existingFile) {
            existingFile.findings += count;
            existingFile.stats = fileStats;
          } else {
            currentLevel.push({
              name: fileName,
              fullPath: filePath,
              children: [],
              findings: count,
              stats: fileStats
            });
          }
        }
      });

      // count findings and aggregate stats for directories
      function countFindings(node) {
        if (node.children.length === 0) {
          return node.findings;
        } else {
          node.findings = node.children.reduce((sum, child) => {
            return sum + countFindings(child);
          }, 0);
          const merged = {};
          node.children.forEach(child => {
            Object.keys(child.stats || {}).forEach(k => {
              merged[k] = (merged[k] || 0) + child.stats[k];
            });
          });
          node.stats = merged;
          return node.findings;
        }
      }
      items.forEach(countFindings);
      this.treeItems = items;
    },

    itemExpanded(expandedItem) {
      if (expandedItem.item.sameReports) return;

      const bugHash = expandedItem.item.bugHash;
      ccService.getSameReports(bugHash).then(sameReports => {
        expandedItem.item.sameReports = sameReports;
      });
    },

    i64ToNum(val) {
      if (val == null) return 0;
      if (typeof val === "number") return val;
      if (typeof val.toNumber === "function")
        return val.toNumber();
      if (val.buffer) {
        let n = 0;
        for (let i = 0; i < val.buffer.length; i++) {
          n = n * 256 + val.buffer[i];
        }
        return n;
      }
      return Number(val) || 0;
    },

    fetchFileSeverities() {
      const PAGE = 500;
      const allStats = {};

      const fetchPage = offset => {
        ccService.getClient().getFileCountsSummary(
          this.runIds, this.reportFilter,
          this.cmpData, PAGE, offset,
          handleThriftError(res => {
            const keys = Object.keys(res || {});

            keys.forEach(filePath => {
              const summary = res[filePath];
              const stats = {};

              Object.keys(summary || {}).forEach(key => {
                const n = this.i64ToNum(summary[key]);
                if (!n) return;

                if (key === "reports") {
                  stats.reports = n;
                } else if (key.startsWith("severity:")) {
                  const name = key.substring(9).toLowerCase();
                  stats[name] = (stats[name] || 0) + n;
                } else if (key.startsWith("review_status:")) {
                  const name = key.substring(14);
                  stats[name] = (stats[name] || 0) + n;
                }
              });

              allStats[filePath] = stats;
            });

            if (keys.length >= PAGE) {
              fetchPage(offset + PAGE);
            } else {
              this.fileSeverities = Object.assign({}, allStats);

              // Build allReportsFileCounts from the summary
              // so the tree doesn't depend on getFileCounts.
              const fileCounts = {};
              Object.keys(allStats).forEach(fp => {
                fileCounts[fp] = allStats[fp].reports || 0;
              });
              this.allReportsFileCounts = fileCounts;
            }
          })
        );
      };

      fetchPage(0);
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

      this.fetchFileSeverities();

    }


  }
};
</script>

<style lang="scss" scoped>
.v-btn-toggle .v-btn--active {
  background-color: #2280c3 !important;
  color: #fff !important;
}

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

.tree-view-container {
  position: relative;
  overflow-y: auto;
  height: calc(100vh - 150px);
}

.tree-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: white;
  display: flex;
  align-items: center;
  padding: 4px 8px 4px 40px;
  font-size: 0.75em;
  font-weight: bold;
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}

.tree-header-name {
  flex: 1;
  min-width: 200px;
}

.tree-header-cell {
  width: 50px;
  text-align: center;
  flex-shrink: 0;
}

.tree-row {
  display: flex;
  align-items: center;
  width: 100%;
}

.tree-item-label {
  flex: 1;
  min-width: 200px;
  font-size: 0.85em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &.clickable {
    cursor: pointer;

    &:hover {
      text-decoration: underline;
      color: var(--v-primary-base);
    }
  }
}

.tree-stat-cell {
  width: 50px;
  text-align: center;
  flex-shrink: 0;
  font-size: 0.8em;
}

</style>
