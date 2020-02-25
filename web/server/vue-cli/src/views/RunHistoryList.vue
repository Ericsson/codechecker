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
      :server-items-length.sync="totalItems"
      :footer-props="{
        itemsPerPageOptions: [50, 100, 250, 500, -1]
      }"
      :must-sort="true"
      item-key="name"
    >
      <template v-slot:top>
        <v-toolbar flat class="mb-4">
          <v-row>
            <v-col>
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
          </v-row>
        </v-toolbar>
      </template>
      <template #item.runName="{ item }">
        <router-link
          :to="{ name: 'reports', query: { run: item.runName } }"
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
        {{ item.$codeCheckerVersion }}
      </template>
    </v-data-table>
  </v-card>
</template>

<script>
import {
  AnalyzerStatisticsBtn,
  AnalyzerStatisticsDialog
} from "@/components/Run";
import { StrToColorMixin } from "@/mixins";

import { ccService } from "@cc-api";
import { RunFilter } from "@cc/report-server-types";

export default {
  name: "RunHistoryList",
  components: {
    AnalyzerStatisticsBtn,
    AnalyzerStatisticsDialog
  },
  mixins: [ StrToColorMixin ],

  data() {
    return {
      runNameSearch: null,
      showCheckCommandDialog: false,
      analyzerStatisticsDialog: false,
      selectedRunHistoryId: null,
      checkCommand: null,
      pagination: {
        page: 1,
        itemsPerPage: 50,
        sortBy: [],
        sortDesc: []
      },
      totalItems: 0,
      loading: false,
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
    }
  },

  watch: {
    runNameSearch: function(newValue) {
      this.fetchRunHistories();

      var queryParams = Object.assign({}, this.$route.query);
      if (queryParams["run"] !== newValue) {
        queryParams["run"] = newValue;
        this.$router.push({ query: queryParams });
      }
    }
  },

  created() {
    this.runNameSearch = this.$router.currentRoute.query["run"];
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

      const filter = null;

      // Get total item count.
      ccService.getClient().getRunHistoryCount(runIds, filter,
      (err, totalItems) => {
        this.totalItems = totalItems.toNumber();
      });

      
      const limit = this.pagination.itemsPerPage;
      const offset = this.pagination.page - 1;

      ccService.getClient().getRunHistory(runIds, limit, offset, filter,
      (err, histories) => {
        this.histories = histories;
      });
    },

    // TODO: Same function in the BaselineRunFilter component.
    async getRunIdsByRunName(runName) {
      const runFilter = new RunFilter({ names: [ runName ] });
      const limit = null;
      const offset = null;
      const sortMode = null;

      return new Promise(resolve => {
        ccService.getClient().getRunData(runFilter, limit, offset, sortMode,
        (err, runs) => {
          resolve(runs.map(run => run.runId));
        });
      });
    },

    openCheckCommandDialog(history) {
      ccService.getClient().getCheckCommand(history.id, null,
      (err, checkCommand) => {
        if (!checkCommand) {
          checkCommand = "Unavailable!";
        }
        this.checkCommand = checkCommand;
        this.showCheckCommandDialog = true;
      });
    },

    closeCheckCommandDialog() {
      this.showCheckCommandDialog = false;
      this.checkCommand = null;
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
