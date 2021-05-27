<template>
  <v-list-item two-line>
    <v-list-item-content>
      <v-list-item-title>
        <router-link
          :to="{ name: 'reports',
                 query: {
                   ...defaultReportFilterValues,
                   ...reportFilterQuery
                 }
          }"
          class="name mr-2"
        >
          {{ name }}
        </router-link>

        <run-description
          v-if="description"
          :value="description"
        />

        <version-tag
          v-if="versionTag"
          :value="versionTag"
        />
      </v-list-item-title>

      <v-list-item-subtitle>
        <show-statistics-btn :extra-queries="statisticsFilterQuery" />

        <v-divider
          class="mx-2 d-inline"
          inset
          vertical
        />

        <analysis-info-btn
          @click="openAnalysisInfoDialog(id)"
        />

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
          <detection-status-icon class="mr-1" :status="parseInt(status)" />
          ({{ value }})
        </v-btn>
      </v-list-item-subtitle>
    </v-list-item-content>
  </v-list-item>
</template>

<script>
import { mapGetters } from "vuex";
import { RunDescription } from "@/components/Run";

import { defaultReportFilterValues } from "@/components/Report/ReportFilter";
import { defaultStatisticsFilterValues } from "@/components/Statistics";

import { DetectionStatusMixin } from "@/mixins";
import { DetectionStatusIcon } from "@/components/Icons";
import AnalysisInfoBtn from "./AnalysisInfoBtn";
import ShowStatisticsBtn from "./ShowStatisticsBtn";
import VersionTag from "./VersionTag";

export default {
  name: "RunNameColumn",
  components: {
    DetectionStatusIcon,
    RunDescription,
    AnalysisInfoBtn,
    ShowStatisticsBtn,
    VersionTag
  },
  mixins: [ DetectionStatusMixin ],
  props: {
    id: { type: Object, required: true },
    name: { type: String, required: true },
    description: { type: String, default: null },
    versionTag: { type: String, default: null },
    detectionStatusCount: { type: Object, default: () => {} },
    showRunHistory: { type: Boolean, default: true },
    openAnalysisInfoDialog: { type: Function, default: () => {} },
    reportFilterQuery: { type: Object, default: () => {} },
    statisticsFilterQuery: { type: Object, default: () => {} },
  },
  data() {
    return {
      defaultReportFilterValues,
      defaultStatisticsFilterValues
    };
  },
  computed: {
    ...mapGetters([
      "queries"
    ])
  }
};
</script>

<style lang="scss" scoped>
.v-list-item__title {
  white-space: normal;
}
</style>