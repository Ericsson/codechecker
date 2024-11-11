<template>
  <select-option
    :id="id"
    title="Latest Review Status"
    :bus="bus"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <review-status-icon :status="item.id" />
    </template>

    <template v-slot:append-toolbar-title>
      <tooltip-help-icon>
        Filter reports by the <b>latest</b> review status.<br><br>

        Reports can be assigned a review status of the following values:
        <ul>
          <li>
            <b>Unreviewed</b>: Nobody has seen this report.
          </li>
          <li>
            <b>Confirmed:</b> This is really a bug.
          </li>
          <li>
            <b>False positive:</b> This is not a bug.
          </li>
          <li>
            <b>Intentional:</b> This report is a bug but we don't want to fix
            it.
          </li>
        </ul>
      </tooltip-help-icon>

      <selected-toolbar-title-items
        v-if="selectedItems"
        :value="selectedItems"
      />
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import { ReportFilter, ReviewStatus } from "@cc/report-server-types";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { ReviewStatusIcon } from "@/components/Icons";
import { ReviewStatusMixin } from "@/mixins";

import { SelectOption, SelectedToolbarTitleItems } from "./SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "ReviewStatusFilter",
  components: {
    SelectOption,
    ReviewStatusIcon,
    SelectedToolbarTitleItems,
    TooltipHelpIcon
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

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.reviewStatus = null;

      return new Promise(resolve => {
        ccService.getClient().getReviewStatusCounts(this.runIds, reportFilter,
          this.cmpData, handleThriftError(res => {
            resolve(Object.keys(ReviewStatus).map(status => {
              const id = ReviewStatus[status];
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
