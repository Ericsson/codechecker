<template>
  <v-select
    label="Select same report"
    :items="items"
    item-text="label"
    item-value="id"
    dense
    solo
    @input="selectSameReport"
  >
    <template v-slot:selection="{ item }">
      <v-list-item-icon class="mr-2">
        <detection-status-icon :status="item.report.detectionStatus" />
      </v-list-item-icon>

      <v-list-item-content>
        <v-list-item-title>{{ item.runName }}:{{ item.report.checkedFile }}:L{{ item.report.line }} [{{ item.report.bugPathLength }}]</v-list-item-title>
      </v-list-item-content>
    </template>

    <template v-slot:item="{ item }">
      <v-list-item-icon class="mr-2">
        <detection-status-icon :status="item.report.detectionStatus" />
      </v-list-item-icon>

      <v-list-item-title>
        <b>
          {{ item.runName }}:{{ item.report.checkedFile }}:L{{ item.report.line }} [{{ item.report.bugPathLength }}]
        </b>
      </v-list-item-title>
    </template>
  </v-select>
</template>

<script>
import VSelect from "Vuetify/VSelect/VSelect";
import {
  VListItemContent,
  VListItemIcon,
  VListItemTitle
} from "Vuetify/VList";

import { ccService } from '@cc-api';
import {
  MAX_QUERY_SIZE,
  ReportFilter,
  RunFilter,
  SortMode,
  SortType,
  Order
} from "@cc/report-server-types";

import { DetectionStatusIcon } from "@/components/icons";

export default {
  name: "SelectSameReport",
  components: {
    VSelect, VListItemContent, VListItemIcon, VListItemTitle,
    DetectionStatusIcon
  },
  props: {
    report: { type: Object, default: null }
  },
  data() {
    return {
      items: [ ]
    };
  },
  watch: {
    report() {
      this.getSameReports();
    }
  },

  methods: {
    getSameReports() {
      var reportFilter = new ReportFilter({
        reportHash: [ this.report.bugHash ]
      });

      const sortMode = new SortMode({
        type: SortType.FILENAME,
        ord: Order.ASC
      });

      ccService.getClient().getRunResults(null, MAX_QUERY_SIZE, 0, [ sortMode ],
      reportFilter, null, false, (err, res) => {
        this.getRuns(res).then(runs => {
          this.items = res.map((report) => {
            const run = runs.find(run => run.runId.equals(report.runId)) || {};

            return {
              id: report.reportId,
              report: report,
              runName: run.name
            };
          });
        });
      });
    },

    getRuns(reports) {
      const runFilter = new RunFilter({
        ids: reports.map(report => report.runId)
      });

      return new Promise((resolve) => {
        ccService.getClient().getRunData(runFilter, null, 0, null,
        (err, res) => {
          resolve(res);
        });
      });
    },

    selectSameReport(value) {
      console.log("Select same report", value);
    }
  }
}
</script>