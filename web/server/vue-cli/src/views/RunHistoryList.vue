<template>
  <v-card flat>
    <!-- TODO: Refactor this component and move things which are common
         with RunList component into separate components. -->
    <v-dialog
      v-model="showCheckCommandDialog"
      content-class="check-command"
      width="500"
    >
      <v-card>
        <v-card-title
          class="headline primary white--text"
          primary-title
        >
          Check command

          <v-spacer />

          <v-btn icon dark @click="showCheckCommandDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text>
          <v-container>
            {{ checkCommand }}
          </v-container>
        </v-card-text>
      </v-card>
    </v-dialog>

    <analyzer-statistics-dialog
      :value.sync="analyzerStatisticsDialog"
      :run-history-id="selectedRunHistoryId"
    />

    <v-data-table
      :headers="headers"
      :items="formattedRunHistories"
      :options.sync="pagination"
      :loading="loading"
      loading-text="Loading run histories..."
      :server-items-length.sync="totalItems"
      :footer-props="footerProps"
      :must-sort="true"
      item-key="name"
    >
      <template v-slot:top>
        <v-toolbar flat class="mb-4">
          <v-row>
            <v-col cols="3">
              <v-text-field
                v-model="runNameSearch"
                class="search-run-name"
                prepend-inner-icon="mdi-magnify"
                label="Filter by run name..."
                clearable
                single-line
                hide-details
                outlined
                solo
                flat
                dense
              />
            </v-col>
            <v-col cols="3">
              <v-text-field
                v-model="runTagSearch"
                class="search-run-tag"
                prepend-inner-icon="mdi-tag"
                label="Filter by run tag..."
                clearable
                single-line
                hide-details
                outlined
                solo
                flat
                dense
              />
            </v-col>
            <v-col align="right">
              <v-btn
                color="primary"
                class="diff-run-history-btn mr-2"
                outlined
                :to="diffTargetRoute"
                :disabled="isDiffBtnDisabled"
              >
                <v-icon left>
                  mdi-select-compare
                </v-icon>
                Diff
              </v-btn>

              <v-btn
                icon
                title="Reload run history"
                color="primary"
                @click="fetchRunHistories"
              >
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </v-col>
          </v-row>
        </v-toolbar>
      </template>
      <template #item.runName="{ item }">
        <run-name-column
          :id="item.id.toNumber()"
          :name="item.runName"
          :description="item.description"
          :report-filter-query="getReportFilterQuery(item)"
          :statistics-filter-query="getStatisticsFilterQuery(item)"
          :show-run-history="false"
          :open-check-command-dialog="openCheckCommandDialog"
        />
      </template>

      <template #item.analyzerStatistics="{ item }">
        <analyzer-statistics-btn
          v-if="Object.keys(item.analyzerStatistics).length"
          :value="item.analyzerStatistics"
          @click.native="openAnalyzerStatisticsDialog(item)"
        />
      </template>

      <template #item.time="{ item }">
        <v-chip
          class="ma-2"
          color="primary"
          outlined
        >
          <v-icon left>
            mdi-calendar-range
          </v-icon>
          {{ item.time | prettifyDate }}
        </v-chip>
      </template>

      <template #item.user="{ item }">
        <v-chip
          class="ma-2"
          color="success"
          outlined
        >
          <v-icon left>
            mdi-account
          </v-icon>
          {{ item.user }}
        </v-chip>
      </template>

      <template #item.versionTag="{ item }">
        <v-chip
          v-if="item.versionTag"
          outlined
        >
          <v-avatar left>
            <v-icon
              :color="strToColor(item.versionTag)"
            >
              mdi-tag-outline
            </v-icon>
          </v-avatar>
          <span
            class="grey--text text--darken-3"
          >
            {{ item.versionTag }}
          </span>
        </v-chip>
      </template>

      <template #item.codeCheckerVersion="{ item }">
        <span :title="item.codeCheckerVersion">
          {{ item.$codeCheckerVersion }}
        </span>
      </template>

      <template #item.diff="{ item }">
        <v-row class="flex-nowrap">
          <v-checkbox
            v-model="selectedBaselineTags"
            :value="item"
            multiple
          />

          <v-checkbox
            v-model="selectedNewcheckTags"
            :value="item"
            multiple
          />
        </v-row>
      </template>
    </v-data-table>
  </v-card>
</template>

<script>
import _ from "lodash";
import { format, max, min, parse } from "date-fns";

import { defaultReportFilterValues } from "@/components/Report/ReportFilter";
import { defaultStatisticsFilterValues } from "@/components/Statistics";

import {
  AnalyzerStatisticsBtn,
  AnalyzerStatisticsDialog,
  RunNameColumn
} from "@/components/Run";
import { StrToColorMixin } from "@/mixins";

import { ccService, handleThriftError } from "@cc-api";
import { RunFilter, RunHistoryFilter } from "@cc/report-server-types";

export default {
  name: "RunHistoryList",
  components: {
    AnalyzerStatisticsBtn,
    AnalyzerStatisticsDialog,
    RunNameColumn
  },
  mixins: [ StrToColorMixin ],

  data() {
    const itemsPerPageOptions = [ 25, 100, 250, 500 ];

    const page = parseInt(this.$router.currentRoute.query["page"]) || 1;
    const itemsPerPage =
      parseInt(this.$router.currentRoute.query["items-per-page"]) ||
      itemsPerPageOptions[0];
    const sortBy = this.$router.currentRoute.query["sort-by"];
    const sortDesc = this.$router.currentRoute.query["sort-desc"];

    const runNameSearch = this.$router.currentRoute.query["run"] || null;
    const runTagSearch = this.$router.currentRoute.query["run-tag"] || null;

    return {
      runNameSearch: runNameSearch,
      runTagSearch: runTagSearch,
      showCheckCommandDialog: false,
      analyzerStatisticsDialog: false,
      selectedRunHistoryId: null,
      checkCommand: null,
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
      selectedBaselineTags: [],
      selectedNewcheckTags: [],
      headers: [
        {
          text: "Name",
          value: "runName",
          sortable: false
        },
        {
          text: "Analyzer statistics",
          value: "analyzerStatistics",
          sortable: false
        },
        {
          text: "Storage date",
          value: "time",
          align: "center",
          sortable: false
        },
        {
          text: "User",
          value: "user",
          align: "center",
          sortable: false
        },
        {
          text: "Version tag",
          value: "versionTag",
          sortable: false
        },
        {
          text: "CodeChecker version",
          value: "codeCheckerVersion",
          align: "center",
          sortable: false
        },
        {
          text: "Diff",
          value: "diff",
          align: "center",
          sortable: false
        }
      ],
      histories: []
    };
  },

  computed: {
    formattedRunHistories() {
      return this.histories.map(history => {
        const ccVersion = this.prettifyCCVersion(history.codeCheckerVersion);

        return {
          ...history,
          $codeCheckerVersion: ccVersion
        };
      });
    },

    isDiffBtnDisabled() {
      return !this.selectedBaselineTags.length ||
             !this.selectedNewcheckTags.length;
    },

    diffTargetRoute() {
      const urlState = {};

      const { runs: bRuns, tags: bTags, times: firstDetectionDates } =
        this.getSelectedTagData(this.selectedBaselineTags);

      urlState["run"] = bRuns;
      urlState["run-tag"] = bTags.length ? bTags : undefined;
      if (firstDetectionDates.length) {
        const minDate = min(firstDetectionDates.map(d =>
          parse(d, "yyyy-MM-dd HH:mm:ss.SSSSSS", new Date())));
        urlState["first-detection-date"] =
          format(minDate, "yyyy-MM-dd HH:mm:ss");
      }

      const { runs: nRuns, tags: nTags, times: fixDates } =
        this.getSelectedTagData(this.selectedNewcheckTags);

      urlState["newcheck"] = nRuns;
      urlState["run-tag-newcheck"] = nTags.length ? nTags : undefined;
      if (fixDates.length) {
        const maxDate = max(fixDates.map(d =>
          parse(d, "yyyy-MM-dd HH:mm:ss.SSSSSS", new Date())));

        // We need to round the date upward because in the url we will save
        // the dates without milliseconds.
        maxDate.setMilliseconds(1000);

        urlState["fix-date"] = format(maxDate, "yyyy-MM-dd HH:mm:ss");
      }

      return {
        name: "reports",
        query: {
          ...this.$router.currentRoute.query,
          ...urlState
        }
      };
    },
  },

  watch: {
    pagination: {
      handler() {
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

        this.fetchRunHistories();
      },
      deep: true
    },

    runNameSearch: {
      handler: _.debounce(function () {
        this.$router.replace({
          query: {
            ...this.$route.query,
            "run": this.runNameSearch ? this.runNameSearch : undefined
          }
        }).catch(() => {});

        if (this.pagination.page !== 1) {
          this.pagination.page = 1;
        } else {
          this.fetchRunHistories();
        }
      }, 250)
    },

    runTagSearch: {
      handler: _.debounce(function () {
        this.$router.replace({
          query: {
            ...this.$route.query,
            "run-tag": this.runTagSearch ? this.runTagSearch : undefined
          }
        }).catch(() => {});

        if (this.pagination.page !== 1) {
          this.pagination.page = 1;
        } else {
          this.fetchRunHistories();
        }
      }, 250)
    },
  },

  methods: {
    async fetchRunHistories() {
      this.loading = true;

      let runIds = null;
      if (this.runNameSearch) {
        runIds = await this.getRunIdsByRunName(this.runNameSearch);
        if (!runIds.length) {
          this.histories = [];
          this.loading = false;
          return;
        }
      }

      const filter = new RunHistoryFilter({
        tagNames: this.runTagSearch ? [ `*${this.runTagSearch}*` ] : null
      });

      // Get total item count.
      ccService.getClient().getRunHistoryCount(runIds, filter,
        (err, totalItems) => {
          this.totalItems = totalItems.toNumber();
        });

      
      const limit = this.pagination.itemsPerPage;
      const offset = limit * (this.pagination.page - 1);

      ccService.getClient().getRunHistory(runIds, limit, offset, filter,
        handleThriftError(histories => {
          this.histories = histories;
          this.loading = false;
        }));
    },

    // TODO: Same function in the BaselineRunFilter component.
    async getRunIdsByRunName(runName) {
      const runFilter = new RunFilter({ names: [ `*${runName}*` ] });
      const limit = null;
      const offset = null;
      const sortMode = null;

      return new Promise(resolve => {
        ccService.getClient().getRunData(runFilter, limit, offset, sortMode,
          handleThriftError(runs => {
            resolve(runs.map(run => run.runId));
          }));
      });
    },

    openCheckCommandDialog(runHistoryId) {
      ccService.getClient().getCheckCommand(runHistoryId, null,
        handleThriftError(checkCommand => {
          if (!checkCommand) {
            checkCommand = "Unavailable!";
          }
          this.checkCommand = checkCommand;
          this.showCheckCommandDialog = true;
        }));
    },

    closeCheckCommandDialog() {
      this.showCheckCommandDialog = false;
      this.checkCommand = null;
    },

    getSelectedTagData(selected) {
      const runs = [];
      const tags = [];
      const times = [];

      selected.forEach(t => {
        runs.push(t.runName);
        times.push(t.time);

        if (t.versionTag) {
          tags.push(t.versionTag);
        }
      });

      return { runs, tags, times };
    },

    openAnalyzerStatisticsDialog(runHistory) {
      this.selectedRunHistoryId = runHistory.id;
      this.analyzerStatisticsDialog = true;
    },

    // TODO: same function in the RunList component.
    prettifyCCVersion(version) {
      if (!version) return version;

      return version.split(" ")[0];
    },

    getReportFilterQuery(history) {
      return {
        run: history.runName,
        "run-tag": history.versionTag || undefined,
        "fix-date": history.versionTag ? undefined : history.time,
        ...defaultReportFilterValues

      };
    },

    getStatisticsFilterQuery(history) {
      return {
        run: history.runName,
        ...defaultStatisticsFilterValues
      };
    }
  }
};
</script>
