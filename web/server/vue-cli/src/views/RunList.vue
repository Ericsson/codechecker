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
      :items="runs"
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

          <v-btn color="primary" class="mr-2" @click="removeSelectedRuns">
            Delete
          </v-btn>
        </v-toolbar>
      </template>

      <template #item.name="{ item }">
        <router-link
          :to="{ name: 'reports', params: { run: item.name } }"
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

      <template #item.checkCommand="{ item }">
        <v-btn text small color="primary" @click="openCheckCommandDialog(item)">
          Show
        </v-btn>
      </template>

      <template #item.versionTag="{ item }">
        <v-chip
          v-if="item.versionTag"
          color="secondary"
          class="mr-2"
        >
          <v-avatar left>
            <v-icon>mdi-label</v-icon>
          </v-avatar>
          {{ item.versionTag }}
        </v-chip>
      </template>
    </v-data-table>
  </v-card>
</template>

<script>
import VDataTable from "Vuetify/VDataTable/VDataTable";
import VChip from "Vuetify/VChip/VChip";
import VAvatar from "Vuetify/VAvatar/VAvatar";
import VIcon from "Vuetify/VIcon/VIcon";
import { VCard, VCardTitle, VCardText } from "Vuetify/VCard";
import VTextField from "Vuetify/VTextField/VTextField";
import VBtn from "Vuetify/VBtn/VBtn";
import VDialog from "Vuetify/VDialog/VDialog";
import VSpacer from "Vuetify/VGrid/VSpacer";
import VToolbar from "Vuetify/VToolbar/VToolbar";

import { DetectionStatusMixin } from "@/mixins";
import { DetectionStatusIcon } from "@/components/icons";

import { ccService } from '@cc-api';
import { RunFilter } from '@cc/report-server-types';

export default {
  name: 'RunList',
  components: {
    VDataTable, VChip, VAvatar, VIcon, VCard, VCardTitle, VCardText,
    VTextField, VBtn, VDialog, VSpacer, VToolbar,
    DetectionStatusIcon
  },

  mixins: [ DetectionStatusMixin ],

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
      headers: [
        {
          text: "Name",
          value: "name"
        },
        {
          text: "Number of unresolved reports",
          value: "resultCount",
          align: 'center',
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
          value: "runDate"
        },
        {
          text: "Analysis duration",
          value: "duration",
          align: 'center',
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
          value: "codeCheckerVersion"
        }
      ],
      runs: []
    };
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
      const offset = this.pagination.page;
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
          checkCommand = 'Unavailable!';
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
    }
  }
}
</script>
