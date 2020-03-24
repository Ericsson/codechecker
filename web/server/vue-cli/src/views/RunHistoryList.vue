<template>
  <v-card>
    <!-- TODO: Refactor this component and move things which are common
         with RunList component into separate components. -->
    <v-dialog v-model="showCheckCommandDialog" width="500">
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
                class="mr-2"
                outlined
                :disabled="isDiffBtnDisabled"
                @click="diffSelectedRunTags"
              >
                <v-icon left>
                  mdi-select-compare
                </v-icon>
                Diff
              </v-btn>
            </v-col>
          </v-row>
        </v-toolbar>
      </template>
      <template #item.runName="{ item }">
        <router-link
          :to="{ name: 'reports', query: {
            'run': item.runName,
            'run-tag': item.versionTag,
            'fix-date': item.time
          }}"
        >
          {{ item.runName }}
        </router-link>
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

      <template #item.checkCommand="{ item }">
        <v-btn text small color="primary" @click="openCheckCommandDialog(item)">
          Show
        </v-btn>
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
        <v-row>
          <v-checkbox
            v-model="selectedBaselineTags"
            :value="item"
          />

          <v-checkbox
            v-model="selectedNewcheckTags"
            :value="item"
          />
        </v-row>
      </template>
    </v-data-table>
  </v-card>
</template>

<script>
import _ from "lodash";
import { format, max, min, parse } from "date-fns";

import {
  AnalyzerStatisticsBtn,
  AnalyzerStatisticsDialog
} from "@/components/Run";
import { StrToColorMixin } from "@/mixins";

import { ccService, handleThriftError } from "@cc-api";
import { RunFilter, RunHistoryFilter } from "@cc/report-server-types";

export default {
  name: "RunHistoryList",
  components: {
    AnalyzerStatisticsBtn,
    AnalyzerStatisticsDialog
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
          sortable: true
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
          sortable: true
        },
        {
          text: "User",
          value: "user",
          align: "center",
          sortable: true
        },
        {
          text: "Check command",
          value: "checkCommand",
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
          sortable: true
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
    }
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
            "name": this.runNameSearch ? this.runNameSearch : undefined
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
      let runIds = null;
      if (this.runNameSearch) {
        runIds = await this.getRunIdsByRunName(this.runNameSearch);
        if (!runIds.length) {
          this.histories = [];
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

    openCheckCommandDialog(history) {
      ccService.getClient().getCheckCommand(history.id, null,
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
      const tags = [];
      const times = [];

      selected.forEach(t => {
        if (t.versionTag)
          tags.push(t.versionTag);

        times.push(t.time);
      });

      return { tags, times };
    },

    diffSelectedRunTags() {
      const urlState = {};

      const { tags: baselineTags, times: firstDetectionDates } =
        this.getSelectedTagData(this.selectedBaselineTags);

      urlState["run-tag"] = baselineTags.length ? baselineTags : undefined;
      if (firstDetectionDates.length) {
        const minDate = min(firstDetectionDates.map(d =>
          parse(d, "yyyy-MM-dd HH:mm:ss.SSSSSS", new Date())));
        urlState["first-detection-date"] =
          format(minDate, "yyyy-MM-dd HH:mm:ss");
      }

      const { tags: newcheckTags, times: fixDates } =
        this.getSelectedTagData(this.selectedNewcheckTags);

      urlState["run-tag-newcheck"] =
        newcheckTags.length ? newcheckTags : undefined;
      if (fixDates.length) {
        const maxDate = max(fixDates.map(d =>
          parse(d, "yyyy-MM-dd HH:mm:ss.SSSSSS", new Date())));
        urlState["fix-date"] = format(maxDate, "yyyy-MM-dd HH:mm:ss");
      }

      this.$router.push({
        name: "reports",
        query: {
          ...this.$router.currentRoute.query,
          ...urlState
        }
      });
    },

    openAnalyzerStatisticsDialog(runHistory) {
      this.selectedRunHistoryId = runHistory.id;
      this.analyzerStatisticsDialog = true;
    },

    // TODO: same function in the RunList component.
    prettifyCCVersion(version) {
      if (!version) return version;

      return version.split(" ")[0];
    }
  }
};
</script>
