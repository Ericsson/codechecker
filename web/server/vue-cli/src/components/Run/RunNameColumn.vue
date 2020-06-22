<template>
  <v-list-item two-line>
    <v-list-item-content>
      <v-list-item-title>
        <router-link
          :to="{ name: 'reports', query: reportFilterQuery }"
          class="name mr-2"
        >
          {{ name }}
        </router-link>

        <run-description
          v-if="description"
          :value="description"
        />

        <v-chip
          v-if="versionTag"
          outlined
          small
        >
          <v-avatar
            class="mr-0"
            left
          >
            <v-icon
              :color="strToColor(versionTag)"
              small
            >
              mdi-tag-outline
            </v-icon>
          </v-avatar>
          <span
            class="grey--text text--darken-3"
          >
            {{ versionTag }}
          </span>
        </v-chip>
      </v-list-item-title>

      <v-list-item-subtitle>
        <v-btn
          v-if="showRunHistory"
          :to="{ name: 'run-history', query: { run: name } }"
          class="show-history"
          title="Show history"
          color="primary"
          small
          text
          icon
        >
          <v-icon>mdi-history</v-icon>
        </v-btn>

        <v-btn
          :to="{ name: 'statistics', query: statisticsFilterQuery }"
          class="show-statistics"
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
          class="show-check-command"
          title="Show check command"
          color="grey darken-1"
          small
          text
          icon
          @click="openCheckCommandDialog(id)"
        >
          <v-icon>mdi-console</v-icon>
        </v-btn>

        <v-divider
          class="mx-2 d-inline"
          inset
          vertical
        />

        <v-btn
          v-for="(value, status) in detectionStatusCount"
          :key="status"
          :to="{ name: 'reports', query: {
            run: name,
            'detection-status': detectionStatusFromCodeToString(status)
          }}"
          class="detection-status-count pa-0"
          small
          text
        >
          <detection-status-icon :status="parseInt(status)" /> ({{ value }})
        </v-btn>
      </v-list-item-subtitle>
    </v-list-item-content>
  </v-list-item>
</template>

<script>
import { RunDescription } from "@/components/Run";

import { DetectionStatusMixin, StrToColorMixin } from "@/mixins";
import { DetectionStatusIcon } from "@/components/Icons";

export default {
  name: "RunNameColumn",
  components: {
    DetectionStatusIcon,
    RunDescription
  },
  mixins: [ DetectionStatusMixin, StrToColorMixin ],
  props: {
    id: { type: Number, required: true },
    name: { type: String, required: true },
    description: { type: String, default: null },
    versionTag: { type: String, default: null },
    detectionStatusCount: { type: Object, default: () => {} },
    showRunHistory: { type: Boolean, default: true },
    openCheckCommandDialog: { type: Function, default: () => {} },
    reportFilterQuery: { type: Object, default: () => {} },
    statisticsFilterQuery: { type: Object, default: () => {} },
  }
};
</script>

<style lang="scss" scoped>
.v-list-item__title {
  white-space: normal;
}
</style>