<template>
  <select-option
    :id="id"
    title="Latest Detection Status"
    :bus="bus"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <detection-status-icon :status="item.id" />
    </template>

    <template v-slot:append-toolbar-title>
      <tooltip-help-icon>
        Filter reports by the <b>latest</b> detection status.<br><br>

        The detection status is the latest state of a bug report in a run. When
        a report id is first detected it will be marked as <b>New</b>. When the
        reports stored again with the same run name then the detection status
        can change to one of the following options:
        <ul>
          <li>
            <b>Resolved:</b> when the bug report can't be found after the
            subsequent storage.
          </li>
          <li>
            <b>Unresolved:</b> when the bug report is still among the results
            after the subsequent storage.
          </li>
          <li>
            <b>Reopened:</b> when a resolved bug appears again.
          </li>
          <li>
            <b>Off:</b> were reported by a checker that is switched off
            during the last analysis which results were stored.
          </li>
          <li>
            <b>Unavailable:</b> were reported by a checker that does not
            exists anymore because it was removed or renamed.
          </li>
        </ul>
      </tooltip-help-icon>

      <tooltip-help-icon
        v-if="reportFilter.isUnique"
      >
        <template v-slot:activator="{ on }">
          <v-icon
            color="error"
            v-on="on"
          >
            mdi-alert
          </v-icon>
        </template>

        Not available in uniqueing mode! Several detection statuses could
        belong to the same bug!
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

import { DetectionStatus, ReportFilter } from "@cc/report-server-types";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { DetectionStatusIcon } from "@/components/Icons";
import { DetectionStatusMixin } from "@/mixins";

import { SelectOption, SelectedToolbarTitleItems } from "./SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "DetectionStatusFilter",
  components: {
    SelectOption,
    DetectionStatusIcon,
    SelectedToolbarTitleItems,
    TooltipHelpIcon
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
