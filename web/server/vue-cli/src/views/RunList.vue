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

    <v-card-title>
      <v-text-field
        v-model="runNameSearch"
        append-icon="mdi-magnify"
        label="Search for runs..."
        single-line
        hide-details
      />
    </v-card-title>
    <v-data-table
      :headers="headers"
      :items="runs"
      item-key="name"
    >
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
          v-for="(value, name) in item.analyzerStatistics"
          :key="name"
        >
          {{ name }}
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

import { DetectionStatusMixin } from "@/mixins";
import { DetectionStatusIcon } from "@/components/icons";

import { ccService } from '@cc-api';
import { RunFilter } from '@cc/report-server-types';

export default {
  name: 'RunList',
  components: {
    VDataTable, VChip, VAvatar, VIcon, VCard, VCardTitle, VCardText,
    VTextField, VBtn, VDialog,
    DetectionStatusIcon
  },

  mixins: [ DetectionStatusMixin ],

  data() {
    return {
      runNameSearch: null,
      showCheckCommandDialog: false,
      checkCommand: null,
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

      const limit = null;
      const offset = null;
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
    }
  }
}
</script>
