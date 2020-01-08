<template>
  <div>
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

      <template #item.checkCommand>
        Show
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
  </div>
</template>

<script>
import VDataTable from "Vuetify/VDataTable/VDataTable";
import VChip from "Vuetify/VChip/VChip";
import VAvatar from "Vuetify/VAvatar/VAvatar";
import VIcon from "Vuetify/VIcon/VIcon";

import { DetectionStatusMixin } from "@/mixins";
import { DetectionStatusIcon } from "@/components/icons";

import { ccService } from '@cc-api';

export default {
  name: 'RunList',
  components: {
    VDataTable, VChip, VAvatar, VIcon,
    DetectionStatusIcon
  },

  mixins: [ DetectionStatusMixin ],

  data() {
    return {
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
          value: "checkCommand"
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

  created() {
    this.fetchRuns();
  },

  methods: {
    fetchRuns() {
      const runFilter = null;
      const limit = null;
      const offset = null;
      const sortMode = null;

      ccService.getClient().getRunData(runFilter, limit, offset, sortMode,
      (err, runs) => {
        this.runs = runs;
      });
    }
  }
}
</script>
