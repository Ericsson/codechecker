<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <report-filter
        :run-ids="runIds"
        :report-filter="reportFilter"
        :cmp-data="cmpData"
      />
    </pane>
    <pane>
      <v-data-table
        :headers="headers"
        :items="reports"
        item-key="name"
      >
        <template #item.checkedFile="{ item }">
          <router-link
            :to="{ name: 'report-detail', query: {
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
import VDataTable from "Vuetify/VDataTable/VDataTable";
import VChip from "Vuetify/VChip/VChip";

import { Splitpanes, Pane } from 'splitpanes';

import { ccService } from '@cc-api';
import { ReportFilter as ReportFilterData } from '@cc/report-server-types';

import { BugPathLengthColorMixin } from '@/mixins';
import { DetectionStatusIcon } from '@/components/icons';
import { ReviewStatusIcon } from '@/components/icons';
import { SeverityIcon } from '@/components/icons';

import ReportFilter from '@/components/ReportFilter/ReportFilter';

export default {
  name: 'Reports',
  components: {
    VDataTable, VChip,
    Splitpanes, Pane,
    DetectionStatusIcon,
    ReviewStatusIcon,
    SeverityIcon,
    ReportFilter
  },
  mixins: [ BugPathLengthColorMixin ],

  data() {
    return {
      runIds: [],
      reportFilter: new ReportFilterData(),
      cmpData: null,
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
          align: 'center'
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
      reports: []
    };
  },

  watch: {
    reportFilter: {
      handler() {
        this.fetchReports();
      },
      deep: true
    }
  },

  created() {
    this.fetchReports();
  },

  methods: {
    fetchReports() {
      const limit = null;
      const offset = null;
      const sortType = null;
      const getDetails = false;

      ccService.getClient().getRunResults(this.runIds, limit, offset, sortType,
      this.reportFilter, this.cmpData, getDetails, (err, reports) => {
        this.reports = reports;
      });
    }
  }
}
</script>
