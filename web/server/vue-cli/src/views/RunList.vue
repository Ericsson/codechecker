<template>
  <v-card flat tile>
    <analysis-info-dialog
      :value.sync="analysisInfoDialog"
      :run-id="selectedRunId"
      :run-history-id="selectedRunHistoryId"
    />

    <analyzer-statistics-dialog
      :value.sync="analyzerStatisticsDialog"
      :run-id="selectedRunId"
      :run-history-id="selectedRunHistoryId"
    />

    <v-data-table
      v-model="selected"
      :headers="headers"
      :items="runs"
      :options.sync="pagination"
      :loading="loading"
      loading-text="Loading runs..."
      :server-items-length.sync="totalItems"
      :footer-props="footerProps"
      :expanded.sync="expanded"
      show-expand
      :must-sort="true"
      :mobile-breakpoint="1000"
      item-key="name"
      show-select
      @item-expanded="runExpanded"
    >
      <template v-slot:top>
        <run-filter-toolbar
          :selected="selected"
          :selected-baseline-runs="selectedBaselineRuns"
          :selected-baseline-tags="selectedBaselineTags"
          :selected-compared-to-runs="selectedComparedToRuns"
          :selected-compared-to-tags="selectedComparedToTags"
          @on-run-filter-changed="onRunFilterChanged"
          @on-run-history-filter-changed="onRunHistoryFilterChanged"
          @update="fetchRuns"
        />
      </template>

      <template v-slot:expanded-item="{ item }">
        <td
          v-if="item.$history"
          :colspan="headers.length + 1"
        >
          <expanded-run
            :histories="item.$history.values"
            :run="item"
            :open-analysis-info-dialog="openAnalysisInfoDialog"
            :open-analyzer-statistics-dialog="openAnalyzerStatisticsDialog"
            :selected-baseline-tags.sync="selectedBaselineTags"
            :selected-compared-to-tags.sync="selectedComparedToTags"
          >
            <v-btn
              v-if="item.$history.hasMore"
              class="load-more-btn mb-4"
              color="primary"
              :loading="loadingMoreRunHistories"
              @click="loadMoreRunHistory(item)"
            >
              Load more (+{{ item.$history.limit }})
            </v-btn>
          </expanded-run>
        </td>
      </template>

      <template #item.name="{ item }">
        <run-name-column
          :id="item.runId"
          :name="item.name"
          :description="item.description"
          :version-tag="item.versionTag"
          :detection-status-count="item.detectionStatusCount"
          :report-filter-query="getReportFilterQuery(item)"
          :statistics-filter-query="getStatisticsFilterQuery(item)"
          :open-analysis-info-dialog="openAnalysisInfoDialog"
        />
      </template>

      <template #item.analyzerStatistics="{ item }">
        <analyzer-statistics-btn
          v-if="Object.keys(item.analyzerStatistics).length"
          :value="item.analyzerStatistics"
          :show-dividers="false"
          tag="div"
          @click.native="openAnalyzerStatisticsDialog(item)"
        />
      </template>

      <template #item.runDate="{ item }">
        <v-chip
          class="ma-2"
          color="primary"
          outlined
        >
          <v-icon left>
            mdi-calendar-range
          </v-icon>
          {{ item.runDate | prettifyDate }}
        </v-chip>
      </template>

      <template #item.duration="{ item }">
        <v-chip
          class="ma-2"
          color="success"
          outlined
        >
          <v-icon left>
            mdi-clock-outline
          </v-icon>
          {{ item.$duration }}
        </v-chip>
      </template>

      <template #item.codeCheckerVersion="{ item }">
        <span :title="item.codeCheckerVersion">
          {{ item.$codeCheckerVersion }}
        </span>
      </template>

      <template #item.diff="{ item }">
        <v-container class="py-0">
          <v-row class="flex-nowrap py-0">
            <v-checkbox
              v-model="selectedBaselineRuns"
              :value="item.name"
              class="ma-0"
              hide-details
              multiple
            />

            <v-checkbox
              v-model="selectedComparedToRuns"
              :value="item.name"
              class="ma-0"
              hide-details
              multiple
            />
          </v-row>
        </v-container>
      </template>
    </v-data-table>
  </v-card>
</template>

<script>
import { mapGetters } from "vuex";
import { ccService, handleThriftError } from "@cc-api";
import {
  Order,
  RunSortMode,
  RunSortType
} from "@cc/report-server-types";

import { AnalysisInfoDialog } from "@/components";
import {
  AnalyzerStatisticsBtn,
  AnalyzerStatisticsDialog,
  ExpandedRun,
  RunFilterToolbar,
  RunNameColumn
} from "@/components/Run";

export default {
  name: "RunList",
  components: {
    AnalyzerStatisticsBtn,
    AnalyzerStatisticsDialog,
    AnalysisInfoDialog,
    ExpandedRun,
    RunNameColumn,
    RunFilterToolbar
  },

  data() {
    const itemsPerPageOptions = [ 25, 50, 100 ];

    const page = parseInt(this.$router.currentRoute.query["page"]) || 1;
    const itemsPerPage =
      parseInt(this.$router.currentRoute.query["items-per-page"]) ||
      itemsPerPageOptions[0];
    const sortBy = this.$router.currentRoute.query["sort-by"];
    const sortDesc = this.$router.currentRoute.query["sort-desc"];

    return {
      initialized: false,
      analysisInfoDialog: false,
      pagination: {
        page: page,
        itemsPerPage: itemsPerPage,
        sortBy: sortBy ? [ sortBy ] : [],
        sortDesc: sortDesc !== undefined ? [ sortDesc === "true" ] : []
      },
      footerProps: {
        itemsPerPageOptions: itemsPerPageOptions
      },
      totalItems: 0,
      loading: false,
      selected: [],
      selectedBaselineRuns: [],
      selectedBaselineTags: [],
      selectedComparedToRuns: [],
      selectedComparedToTags: [],
      analyzerStatisticsDialog: false,
      selectedRunId: null,
      selectedRunHistoryId: null,
      expanded: [],
      loadingMoreRunHistories: false,
      headers: [
        {
          text: "",
          value: "data-table-expand"
        },
        {
          text: "Name",
          value: "name",
          sortable: true
        },
        {
          text: "Number of unresolved reports",
          value: "resultCount",
          align: "center",
          sortable: true
        },
        {
          text: "Analyzer statistics",
          value: "analyzerStatistics",
          sortable: false
        },
        {
          text: "Latest storage date",
          value: "runDate",
          align: "center",
          sortable: true
        },
        {
          text: "Analysis duration",
          value: "duration",
          align: "center",
          sortable: true
        },
        {
          text: "CodeChecker version",
          value: "codeCheckerVersion",
          align: "center",
          sortable: true
        },
        {
          text: "Diff",
          value: "diff",
          align: "center",
          sortable: false,
          width: "100px"
        }
      ],
      runs: []
    };
  },

  computed: {
    ...mapGetters("run", [
      "runFilter",
      "runHistoryFilter"
    ])
  },

  watch: {
    pagination: {
      handler() {
        if (!this.initialized) return;

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

        this.updateUrl({
          "items-per-page": itemsPerPage,
          "page": page,
          "sort-by": sortBy,
          "sort-desc": sortDesc,
        });

        this.fetchRuns();
      },
      deep: true
    }
  },

  async mounted() {
    await this.fetchRuns();
    await this.initExpandedItems();

    this.initialized = true;
  },

  methods: {
    onRunFilterChanged() {
      if (this.pagination.page !== 1) {
        this.pagination.page = 1;
      } else {
        this.fetchRuns();
      }
    },

    async onRunHistoryFilterChanged() {
      this.loading = true;

      await Promise.all(this.expanded.map(async run => {
        const { limit, offset } = run.$history;

        const { histories, hasMore } =
          await this.getRunHistory(run.runId, limit + offset);

        run.$history.hasMore = hasMore;
        run.$history.values = histories;
      }));

      this.loading = false;
    },

    async initExpandedItems() {
      const expanded = this.$router.currentRoute.query["expanded"];
      if (!expanded)
        return;

      const expandedItems = JSON.parse(expanded);
      for (const [ key, val ] of Object.entries(expandedItems)) {
        const limit = val.limit;
        const offset = val.offset;
        const runId = +key;

        const run = this.runs.find(r => r.runId.toNumber() === runId);
        const { histories, hasMore } =
          await this.getRunHistory(runId, limit + offset, 0);

        run.$history = {
          limit,
          offset,
          hasMore,
          values: histories
        };

        this.expanded.push(run);
      }
    },

    updateUrl(params) {
      this.$router.replace({
        query: {
          ...this.$route.query,
          ...params
        }
      }).catch(() => {});
    },

    updateExpandedUrlParam() {
      const expanded = this.expanded.reduce((acc, curr) => {
        acc[curr.runId] = {
          limit: curr.$history.limit,
          offset: curr.$history.offset
        };

        return acc;
      }, {});

      this.updateUrl({
        expanded: this.expanded.length ? JSON.stringify(expanded) : undefined
      });
    },

    async loadMoreRunHistory(run) {
      this.loadingMoreRunHistories = true;

      const limit = run.$history.limit;

      const offset = run.$history.offset + limit;
      run.$history.offset = offset;

      const { histories, hasMore } =
        await this.getRunHistory(run.runId, limit, offset);

      run.$history.hasMore = hasMore;
      run.$history.values.push(...histories);

      this.updateExpandedUrlParam();

      this.loadingMoreRunHistories = false;
    },

    async runExpanded(run, limit=10, offset=0) {
      if (run.item.$history) {
        // Use nextTick to wait while expanded array is updated.
        return this.$nextTick(this.updateExpandedUrlParam);
      }

      this.loading = true;

      const { histories, hasMore } =
        await this.getRunHistory(run.item.runId, limit, offset);

      run.item.$history = {
        limit,
        offset,
        hasMore,
        values: histories
      };

      this.updateExpandedUrlParam();

      this.loading = false;
    },

    getRunHistory(runId, limit=10, offset=null) {
      return new Promise(resolve => {
        ccService.getClient().getRunHistory([ runId ], limit, offset,
          this.runHistoryFilter, handleThriftError(histories => {
            resolve({
              hasMore: histories.length === limit,
              histories: histories.map(h => ({
                ...h,
                $codeCheckerVersion:
                  this.prettifyCCVersion(h.codeCheckerVersion)
              }))
            });
          }));
      });
    },

    getSortMode() {
      let type = null;
      switch (this.pagination.sortBy[0]) {
      case "name":
        type = RunSortType.NAME;
        break;
      case "resultCount":
        type = RunSortType.UNRESOLVED_REPORTS;
        break;
      case "duration":
        type = RunSortType.DURATION;
        break;
      case "codeCheckerVersion":
        type = RunSortType.CC_VERSION;
        break;
      default:
        type = RunSortType.DATE;
      }

      const ord = this.pagination.sortDesc[0] === false
        ? Order.ASC : Order.DESC;

      return new RunSortMode({ type: type, ord: ord });
    },

    fetchRuns() {
      this.loading = true;

      // Get total item count.
      ccService.getClient().getRunCount(this.runFilter,
        handleThriftError(totalItems => {
          this.totalItems = totalItems.toNumber();
        }));

      // Get the runs.
      const limit = this.pagination.itemsPerPage;
      const offset = limit * (this.pagination.page - 1);
      const sortMode = this.getSortMode();

      return new Promise(resolve => {
        ccService.getClient().getRunData(this.runFilter, limit, offset,
          sortMode, handleThriftError(runs => {
            this.runs = runs.map(r => {
              const version = this.prettifyCCVersion(r.codeCheckerVersion);

              // Init run history by the expanded array.
              const oldRun = this.expanded.find(e =>
                e.runId.toNumber() === r.runId.toNumber());

              return {
                ...r,
                $history: oldRun ? oldRun.$history : null,
                $duration: this.prettifyDuration(r.duration),
                $codeCheckerVersion: version
              };
            });

            this.loading = false;

            resolve(this.runs);
          }));
      });
    },

    openAnalysisInfoDialog(runId, runHistoryId=null) {
      this.selectedRunId = runId;
      this.selectedRunHistoryId = runHistoryId;
      this.analysisInfoDialog = true;
    },

    openAnalyzerStatisticsDialog(report, history=null) {
      this.selectedRunId = report ? report.runId : null;
      this.selectedRunHistoryId = history ? history.id : null;
      this.analyzerStatisticsDialog = true;
    },

    prettifyDuration(seconds) {
      if (seconds >= 0) {
        const durHours = Math.floor(seconds / 3600);
        const durMins  = Math.floor(seconds / 60) - durHours * 60;
        const durSecs  = seconds - durMins * 60 - durHours * 3600;

        const prettyDurHours = (durHours < 10 ? "0" : "") + durHours;
        const prettyDurMins  = (durMins  < 10 ? "0" : "") + durMins;
        const prettyDurSecs  = (durSecs  < 10 ? "0" : "") + durSecs;

        return prettyDurHours + ":" + prettyDurMins + ":" + prettyDurSecs;
      }

      return "";
    },

    prettifyCCVersion(version) {
      if (!version) return version;

      return version.split(" ")[0];
    },

    getReportFilterQuery(run) {
      return {
        run: run.name
      };
    },

    getStatisticsFilterQuery(run) {
      return {
        run: run.name
      };
    }
  }
};
</script>

<style lang="scss" scoped>
.v-data-table ::v-deep tbody tr.v-data-table__expanded__content {
  box-shadow: none;
}
</style>