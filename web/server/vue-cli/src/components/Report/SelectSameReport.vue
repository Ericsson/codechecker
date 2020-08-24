<template>
  <v-select
    v-model="active"
    :items="items"
    :hide-details="true"
    :menu-props="{ contentClass: 'select-same-report-menu' }"
    class="select-same-report small"
    label="Found in"
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
      ccService.getSameReports(this.report.bugHash).then(reports => {
        this.items = reports.map(report => {
          return {
            id: report.reportId,
            runName: report.$runName,
            fileName: report.checkedFile.replace(/^.*[\\/]/, ""),
            line: report.line,
            bugPathLength: report.bugPathLength,
            detectionStatus: report.detectionStatus
          };
        });
      });
    },

    selectSameReport(reportId) {
      this.$emit("update:report", reportId.toNumber());
    }
  }
};
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
