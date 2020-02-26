<template>
  <select-option
    title="Detection status"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
    @clear="clear"
  >
    <template v-slot:icon="{ item }">
      <detection-status-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
import { ccService } from "@cc-api";

import { DetectionStatus, ReportFilter } from "@cc/report-server-types";
import { DetectionStatusIcon } from "@/components/Icons";
import { DetectionStatusMixin } from "@/mixins";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "DetectionStatusFilter",
  components: {
    SelectOption,
    DetectionStatusIcon
  },
  mixins: [ BaseSelectOptionFilterMixin, DetectionStatusMixin ],

  data() {
    return {
      id: "detection-status"
    };
  },

  methods: {
    encodeValue(detectionStatusId) {
      return this.detectionStatusFromCodeToString(detectionStatusId);
    },

    decodeValue(detectionStatusName) {
      return this.detectionStatusFromStringToCode(detectionStatusName);
    },

    updateReportFilter() {
      this.setReportFilter({
        detectionStatus: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "detectionStatus" || !this.selectedItems.length) return;

      this.fetchItems();
    },

    fetchItems() {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.detectionStatus = null;

      ccService.getClient().getDetectionStatusCounts(this.runIds, reportFilter,
        this.cmpData, (err, res) => {
          this.items = Object.keys(DetectionStatus).map(status => {
            const id = DetectionStatus[status];
            return {
              id: id,
              title: this.encodeValue(id),
              count: res[id] !== undefined ? res[id] : 0
            };
          });
          this.updateSelectedItems();
          this.loading = false;
        });
    }
  }
};
</script>
