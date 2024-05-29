<template>
  <select-option
    :id="id"
    title="Report Status"
    :bus="bus"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <report-status-icon :status="item.id" />
    </template>

    <template v-slot:append-toolbar-title>
      <tooltip-help-icon>
        Filter reports by the <b>latest</b> report status.<br><br>

        A report can be outstanding or closed.
        Outstanding reports are potential bugs.
        Closed reports are fixed bugs, suppressed, resolved
        or unavailable reports.

        <br><br>

        The report is <b>outstanding</b> when its
        <ul>
          <li>
            <b>Review status</b>: is unreviewed or confirmed
          </li>
          <b>and</b>
          <li>
            <b>Detection status</b>: is new, unresolved or reopened.
          </li>
        </ul>
        The report is <b>closed</b> when its
        <ul>
          <li>
            <b>Review status</b>: is false positive, intentional
          </li>
          <b>or</b>
          <li>
            <b>Detection status</b>: is resolved, off or unavailable.
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

import { ReportFilter, ReportStatus } from "@cc/report-server-types";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { ReportStatusIcon } from "@/components/Icons";
import { ReportStatusMixin } from "@/mixins";

import { SelectOption, SelectedToolbarTitleItems } from "./SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "ReportStatusFilter",
  components: {
    SelectOption,
    ReportStatusIcon,
    SelectedToolbarTitleItems,
    TooltipHelpIcon
  },
  mixins: [ BaseSelectOptionFilterMixin, ReportStatusMixin ],

  data() {
    return {
      id: "report-status"
    };
  },

  methods: {
    encodeValue(reportStatusId) {
      return this.reportStatusFromCodeToString(reportStatusId);
    },

    decodeValue(reportStatusName) {
      return this.reportStatusFromStringToCode(reportStatusName);
    },

    updateReportFilter() {
      this.setReportFilter({
        reportStatus: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "reportStatus") return;
      this.update();
    },

    fetchItems() {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.reportStatus = null;

      return new Promise(resolve => {
        ccService.getClient().getReportStatusCounts(this.runIds, reportFilter,
          this.cmpData, handleThriftError(res => {
            resolve(Object.keys(ReportStatus).map(status => {
              const id = ReportStatus[status];
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
  