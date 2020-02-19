<template>
  <v-select
    v-model="active"
    :items="items"
    :hide-details="true"
    class="small"
    label="Also found in"
    item-text="label"
    item-value="id"
    height="0"
    flat
    dense
    solo
    @input="selectSameReport"
  >
    <template v-slot:selection="{ item }">
      <select-same-report-item :item="item" />
    </template>

    <template v-slot:item="{ item }">
      <select-same-report-item :item="item" />
    </template>
  </v-select>
</template>

<script>
import { ccService } from "@cc-api";
import {
  MAX_QUERY_SIZE,
  ReportFilter,
  RunFilter,
  SortMode,
  SortType,
  Order
} from "@cc/report-server-types";

import SelectSameReportItem from "./SelectSameReportItem";

export default {
  name: "SelectSameReport",
  components: {
    SelectSameReportItem
  },
  props: {
    report: { type: Object, default: null }
  },
  data() {
    return {
      items: [],
      active: null
    };
  },
  watch: {
    report() {
      this.init();
    }
  },

  mounted() {
    this.init();
  },

  methods: {
    init() {
      if (!this.report) return;

      this.active = this.report.reportId;
      this.getSameReports();
    },

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
              runName: run.name,
              fileName: report.checkedFile.replace(/^.*[\\/]/, ""),
              line: report.line,
              bugPathLength: report.bugPathLength,
              detectionStatus: report.detectionStatus
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

    selectSameReport(reportId) {
      this.$emit("update:report", reportId.toNumber());
    }
  }
}
</script>

<style lang="scss" scoped>
::v-deep .v-select__selections input {
  display: none;
}

.v-select.v-text-field--outlined {
  ::v-deep .theme--light.v-label {
    background-color: #fff;
  }
}
</style>
