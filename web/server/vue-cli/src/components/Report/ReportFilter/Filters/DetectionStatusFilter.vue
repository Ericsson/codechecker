<template>
  <select-option
    :id="id"
    title="Detection status"
    :bus="bus"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <detection-status-icon :status="item.id" />
    </template>

    <template v-slot:prepend-toolbar-title>
      <v-icon
        v-if="reportFilter.isUnique"
        color="error"
        :title="uniqueingErrorTitle"
      >
        mdi-alert
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

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
      id: "detection-status",
      uniqueingErrorTitle: "Not available in uniqueing mode! Several " +
        "detection statuses could belong to the same bug!"
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
      if (key === "detectionStatus") return;
      this.update();
    },

    fetchItems() {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.detectionStatus = null;

      return new Promise(resolve => {
        ccService.getClient().getDetectionStatusCounts(this.runIds,
          reportFilter, this.cmpData, handleThriftError(res => {
            resolve(Object.keys(DetectionStatus).map(status => {
              const id = DetectionStatus[status];
              return {
                id: id,
                title: this.encodeValue(id),
                count: res[id] !== undefined ? res[id].toNumber() : 0
              };
            }));
            this.loading = false;
          }));
      });
    }
  }
};
</script>
