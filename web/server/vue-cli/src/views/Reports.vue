<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <report-filter
        v-fill-height
        :namespace="namespace"
        @refresh="fetchReports"
      />
    </pane>
    <pane>
      <v-data-table
        v-fill-height
        :headers="headers"
        :items="reports"
        :loading="loading"
        loading-text="Loading reports..."
        item-key="name"
      >
        <template #item.bugHash="{ item }">
          <span :title="item.bugHash">
            {{ item.bugHash | truncate(10) }}
          </span>
        </template>

        <template #item.checkedFile="{ item }">
          <router-link
            :to="{ name: 'report-detail', query: {
              ...$router.currentRoute.query,
              reportId: item.reportId ? item.reportId : undefined,
              reportHash: item.reportId ? undefined : item.bugHash
            }}"
          >
            {{ item.checkedFile }}
          </router-link>
        </template>

        <template #item.severity="{ item }">
          <severity-icon :status="item.severity" />
        </template>

        <template #item.bugPathLength="{ item }">
          <v-chip :color="getBugPathLenColor(item.bugPathLength)">
            {{ item.bugPathLength }}
          </v-chip>
        </template>

        <template #item.reviewData="{ item }">
          <review-status-icon :status="parseInt(item.reviewData.status)" />
        </template>

        <template #item.detectionStatus="{ item }">
          <detection-status-icon :status="parseInt(item.detectionStatus)" />
        </template>
      </v-data-table>
    </pane>
  </splitpanes>
</template>

<script>
import { Splitpanes, Pane } from "splitpanes";

import { mapGetters } from "vuex";

import { ccService } from "@cc-api";

import { FillHeight } from "@/directives";
import { BugPathLengthColorMixin } from "@/mixins";
import { DetectionStatusIcon } from "@/components/Icons";
import { ReviewStatusIcon } from "@/components/Icons";
import { SeverityIcon } from "@/components/Icons";

import { ReportFilter } from "@/components/Report/ReportFilter";

const namespace = "report";

export default {
  name: "Reports",
  components: {
    Splitpanes,
    Pane,
    DetectionStatusIcon,
    ReviewStatusIcon,
    SeverityIcon,
    ReportFilter
  },
  directives: { FillHeight },
  mixins: [ BugPathLengthColorMixin ],

  data() {
    return {
      headers: [
        {
          text: "Report hash",
          value: "bugHash"
        },
        {
          text: "File",
          value: "checkedFile"
        },
        {
          text: "Message",
          value: "checkerMsg"
        },
        {
          text: "Checker name",
          value: "checkerId"
        },
        {
          text: "Severity",
          value: "severity"
        },
        {
          text: "Bug path length",
          value: "bugPathLength",
          align: "center"
        },
        {
          text: "Review status",
          value: "reviewData",
          align: "center"
        },
        {
          text: "Detection status",
          value: "detectionStatus",
          align: "center"
        }
      ],
      reports: [],
      namespace: namespace,
      loading: true,
      runIdsUnwatch: null,
      reportFilterUnwatch: null,
      cmpDataUnwatch: null
    };
  },

  computed: {
    ...mapGetters(namespace, {
      runIds: "getRunIds",
      reportFilter: "getReportFilter",
      cmpData: "getCmpData"
    })
  },

  methods: {
    fetchReports() {
      this.loading = true;

      const limit = null;
      const offset = null;
      const sortType = null;
      const getDetails = false;

      ccService.getClient().getRunResults(this.runIds, limit, offset, sortType,
        this.reportFilter, this.cmpData, getDetails, (err, reports) => {
          this.reports = reports;
          this.loading = false;
        });
    }
  }
};
</script>

<style lang="scss" scoped>
.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}
</style>
