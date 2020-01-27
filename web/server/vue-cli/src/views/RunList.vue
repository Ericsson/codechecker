<template>
  <v-card>
    <v-dialog v-model="showCheckCommandDialog" width="500">
      <v-card>
        <v-card-title class="headline" primary-title>
          Check command
        </v-card-title>
        <v-card-text>
          {{ checkCommand }}
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-data-table
      v-model="selected"
      :headers="headers"
      :items="formattedRuns"
      :options.sync="pagination"
      :loading="loading"
      :server-items-length.sync="totalItems"
      :footer-props="{
        itemsPerPageOptions: [20, 50, 100, 500, -1]
      }"
      item-key="name"
      show-select
    >
      <template v-slot:top>
        <v-toolbar flat class="mb-4">
          <v-text-field
            v-model="runNameSearch"
            append-icon="mdi-magnify"
            label="Search for runs..."
            single-line
            hide-details
          />

          <v-spacer />

          <v-btn
            color="error"
            class="mr-2"
            outlined
            @click="removeSelectedRuns"
          >
            Delete
          </v-btn>

          <v-btn
            color="primary"
            class="mr-2"
            outlined
            :disabled="isDiffBtnDisabled"
            @click="diffSelectedRuns"
          >
            Diff
          </v-btn>
        </v-toolbar>
      </template>

      <template #item.name="{ item }">
        <router-link
          :to="{ name: 'reports', query: { run: item.name } }"
        >
          {{ item.name }}
        </router-link>
      </template>

      <template #item.detectionStatusCount="{ item }">
        <div
          v-for="(value, name) in item.detectionStatusCount"
          :key="name"
        >
          <detection-status-icon :status="parseInt(name)" /> ({{ value }})
        </div>
      </template>

      <template #item.analyzerStatistics="{ item }">
        <div
          v-for="(stats, analyzer) in item.analyzerStatistics"
          :key="analyzer"
        >
          {{ analyzer }}:
          <span v-if="stats.successful.toNumber() !== 0">
            <v-icon color="#587549">mdi-check</v-icon>
            ({{ stats.successful }})
          </span>
          <span v-if="stats.failed.toNumber() !== 0">
            <v-icon color="#964739">mdi-close</v-icon>
            ({{ stats.failed }})
          </span>
        </div>
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
          {{ item.$runDate }}
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
import { DetectionStatusMixin, StrToColorMixin } from "@/mixins";
import { DetectionStatusIcon } from "@/components/icons";

import { ccService } from "@cc-api";
import { RunFilter } from "@cc/report-server-types";

export default {
  name: "RunList",
  components: {
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
        itemsPerPage: 20
      },
      totalItems: 0,
      loading: false,
      selected: [],
      selectedBaselineRuns: [],
      selectedNewcheckRuns: [],
      headers: [
        {
          text: "Name",
          value: "name"
        },
        {
          text: "Number of unresolved reports",
          value: "resultCount",
          align: "center",
        },
        {
          text: "Detection status",
          value: "detectionStatusCount"
        },
        {
          text: "Analyzer statistics",
          value: "analyzerStatistics"
        },
        {
          text: "Storage date",
          value: "runDate",
          align: "center"
        },
        {
          text: "Analysis duration",
          value: "duration",
          align: "center",
        },
        {
          text: "Check command",
          value: "checkCommand",
          align: "center"
        },
        {
          text: "Version tag",
          value: "versionTag"
        },
        {
          text: "CodeChecker version",
          value: "codeCheckerVersion",
          align: "center"
        },
        {
          text: "Diff",
          value: "diff",
          align: "center"
        }
      ],
      runs: []
    };
  },

  computed: {
    formattedRuns() {
      return this.runs.map((run) => {
        return {
          ...run,
          $duration: this.prettifyDuration(run.duration),
          $runDate: this.prettifyDate(run.runDate),
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
    fetchRuns() {
      const runFilter = this.runNameSearch
        ? new RunFilter({ names: [`*${this.runNameSearch}*`]})
        : null;

      // Get total item count.
      ccService.getClient().getRunCount(runFilter, (err, totalItems) => {
        this.totalItems = totalItems.toNumber();
      });

      // Get the runs.
      const limit = this.pagination.itemsPerPage;
      const offset = this.pagination.page - 1;
      const sortMode = null;

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

    closeCheckCommandDialog() {
      this.showCheckCommandDialog = false;
      this.checkCommand = null;
    },

    removeSelectedRuns() {
      const runFilter = new RunFilter({
        ids: this.selected.map((run) => run.runId)
      });

      ccService.getClient().removeRun(null, runFilter, () => {
        this.fetchRuns();
      });
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

    prettifyDate (date) {
      return date.split(/[.]+/)[0];
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
