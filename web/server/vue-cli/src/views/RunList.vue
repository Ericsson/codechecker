<template>
  <v-card>
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
      :run-id="selectedRunId"
    />

    <v-data-table
      v-model="selected"
      :headers="headers"
      :items="formattedRuns"
      :options.sync="pagination"
      :loading="loading"
      :server-items-length.sync="totalItems"
      :footer-props="{
        itemsPerPageOptions: [50, 100, 250, 500, -1]
      }"
      :must-sort="true"
      item-key="name"
      show-select
    >
      <template v-slot:top>
        <v-toolbar flat class="mb-4">
          <v-row>
            <v-col>
              <v-text-field
                v-model="runNameSearch"
                prepend-inner-icon="mdi-magnify"
                label="Search for runs..."
                single-line
                hide-details
                outlined
                solo
                flat
                dense
              />
            </v-col>

            <v-spacer />

            <v-col align="right">
              <delete-run-btn
                :selected="selected"
                @on-confirm="fetchRuns"
              />

              <v-btn
                color="primary"
                class="mr-2"
                outlined
                :disabled="isDiffBtnDisabled"
                @click="diffSelectedRuns"
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

      <template #item.name="{ item }">
        <v-list-item two-line>
          <v-list-item-content>
            <v-list-item-title>
              <router-link
                :to="{ name: 'reports', query: { run: item.name } }"
                class="mr-2"
              >
                {{ item.name }}
              </router-link>

              <v-chip
                v-if="item.versionTag"
                outlined
                small
              >
                <v-avatar
                  class="mr-0"
                  left
                >
                  <v-icon
                    :color="strToColor(item.versionTag)"
                    small
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
            </v-list-item-title>

            <v-list-item-subtitle>
              <v-btn
                :to="{ name: 'run-history', query: { run: item.name } }"
                title="Show history"
                color="primary"
                small
                text
                icon
              >
                <v-icon>mdi-history</v-icon>
              </v-btn>

              <v-btn
                :to="{ name: 'statistics', query: { run: item.name } }"
                title="Show statistics"
                color="green"
                small
                text
                icon
              >
                <v-icon>mdi-chart-line</v-icon>
              </v-btn>

              <v-divider
                class="mx-2 d-inline"
                inset
                vertical
              />

              <v-btn
                title="Show check command"
                color="orange"
                small
                text
                icon
                @click="openCheckCommandDialog(item)"
              >
                <v-icon>mdi-apple-keyboard-command</v-icon>
              </v-btn>

              <v-divider
                class="mx-2 d-inline"
                inset
                vertical
              />

              <v-btn
                v-for="(value, name) in item.detectionStatusCount"
                :key="name"
                :to="{ name: 'reports', query: {
                  run: item.name,
                  'detection-status': detectionStatusFromCodeToString(name)
                }}"
                class="pa-0"
                small
                text
              >
                <detection-status-icon :status="parseInt(name)" /> ({{ value }})
              </v-btn>
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </template>

      <template #item.analyzerStatistics="{ item }">
        <analyzer-statistics-btn
          v-if="Object.keys(item.analyzerStatistics).length"
          :value="item.analyzerStatistics"
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
        {{ item.$codeCheckerVersion }}
      </template>

      <template #item.diff="{ item }">
        <v-row>
          <v-checkbox
            v-model="selectedBaselineRuns"
            :value="item.name"
          />

          <v-checkbox
            v-model="selectedNewcheckRuns"
            :value="item.name"
          />
        </v-row>
      </template>
    </v-data-table>
  </v-card>
</template>

<script>
import {
  AnalyzerStatisticsBtn,
  AnalyzerStatisticsDialog,
  DeleteRunBtn
} from "@/components/Run";
import { DetectionStatusMixin, StrToColorMixin } from "@/mixins";
import { DetectionStatusIcon } from "@/components/Icons";

import { ccService } from "@cc-api";
import {
  Order,
  RunFilter,
  RunSortType,
  RunSortMode
} from "@cc/report-server-types";

export default {
  name: "RunList",
  components: {
    AnalyzerStatisticsBtn,
    AnalyzerStatisticsDialog,
    DeleteRunBtn,
    DetectionStatusIcon
  },

  mixins: [ DetectionStatusMixin, StrToColorMixin ],

  data() {
    return {
      runNameSearch: null,
      showCheckCommandDialog: false,
      checkCommand: null,
      pagination: {
        page: 1,
        itemsPerPage: 50,
        sortBy: [],
        sortDesc: []
      },
      totalItems: 0,
      loading: false,
      selected: [],
      selectedBaselineRuns: [],
      selectedNewcheckRuns: [],
      analyzerStatisticsDialog: false,
      selectedRunId: null,
      headers: [
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
          text: "Storage date",
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
          sortable: false
        }
      ],
      runs: []
    };
  },

  computed: {
    formattedRuns() {
      return this.runs.map(run => {
        return {
          ...run,
          $duration: this.prettifyDuration(run.duration),
          $codeCheckerVersion: this.prettifyCCVersion(run.codeCheckerVersion)
        };
      });
    },
    isDiffBtnDisabled() {
      return !this.selectedBaselineRuns.length ||
             !this.selectedNewcheckRuns.length;
    }
  },

  watch: {
    pagination: {
      handler() {
        this.fetchRuns();
      },
      deep: true
    },

    showCheckCommandDialog (val) {
      val || this.closeCheckCommandDialog();
    },

    runNameSearch: function(newValue) {
      this.fetchRuns();

      var queryParams = Object.assign({}, this.$route.query);
      if (queryParams["search"] !== newValue) {
        queryParams["search"] = newValue;
        this.$router.push({ query: queryParams });
      }
    }
  },

  created() {
    this.runNameSearch = this.$router.currentRoute.query["search"];
  },

  methods: {
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

      const ord = this.pagination.sortDesc[0] ? Order.DESC : Order.ASC;

      return new RunSortMode({ type: type, ord: ord });
    },

    fetchRuns() {
      const runFilter = this.runNameSearch
        ? new RunFilter({ names: [ `*${this.runNameSearch}*` ]})
        : null;

      // Get total item count.
      ccService.getClient().getRunCount(runFilter, (err, totalItems) => {
        this.totalItems = totalItems.toNumber();
      });

      // Get the runs.
      const limit = this.pagination.itemsPerPage;
      const offset = this.pagination.page - 1;
      const sortMode = this.getSortMode();

      ccService.getClient().getRunData(runFilter, limit, offset, sortMode,
      (err, runs) => {
        this.runs = runs;
      });
    },

    openCheckCommandDialog(report) {
      ccService.getClient().getCheckCommand(null, report.runId,
      (err, checkCommand) => {
        if (!checkCommand) {
          checkCommand = "Unavailable!";
        }
        this.checkCommand = checkCommand;
        this.showCheckCommandDialog = true;
      });
    },

    openAnalyzerStatisticsDialog(report) {
      this.selectedRunId = report.runId;
      this.analyzerStatisticsDialog = true;
    },

    closeCheckCommandDialog() {
      this.showCheckCommandDialog = false;
      this.checkCommand = null;
    },

    diffSelectedRuns() {
      this.$router.push({
        name: "reports",
        query: {
          ...this.$router.currentRoute.query,
          run: this.selectedBaselineRuns,
          newcheck: this.selectedNewcheckRuns
        }});
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
    }
  }
}
</script>
