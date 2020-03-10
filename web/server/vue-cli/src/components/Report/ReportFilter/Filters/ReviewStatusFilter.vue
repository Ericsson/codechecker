<template>
  <select-option
    title="Review Status"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <review-status-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import { ReportFilter, ReviewStatus } from "@cc/report-server-types";
import { ReviewStatusIcon } from "@/components/Icons";
import { ReviewStatusMixin } from "@/mixins";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "ReviewStatusFilter",
  components: {
    SelectOption,
    ReviewStatusIcon
  },
  mixins: [ BaseSelectOptionFilterMixin, ReviewStatusMixin ],

  data() {
    return {
      id: "review-status"
    };
  },

  methods: {
    encodeValue(reviewStatusId) {
      return this.reviewStatusFromCodeToString(reviewStatusId);
    },

    decodeValue(reviewStatusName) {
      return this.reviewStatusFromStringToCode(reviewStatusName);
    },

    updateReportFilter() {
      this.setReportFilter({
        reviewStatus: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "reviewStatus") return;
      this.update();
    },

    fetchItems() {
      this.loading = true;
      this.items = [];

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.reviewStatus = null;

      ccService.getClient().getReviewStatusCounts(this.runIds, reportFilter,
        this.cmpData, handleThriftError(res => {
          this.items = Object.keys(ReviewStatus).map(status => {
            const id = ReviewStatus[status];
            return {
              id: id,
              title: this.encodeValue(id),
              count: res[id] !== undefined ? res[id] : 0
            };
          });
          this.loading = false;
        }));
    }
  }
};
</script>
