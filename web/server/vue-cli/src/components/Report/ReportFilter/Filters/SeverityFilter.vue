<template>
  <select-option
    title="Severity"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <severity-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
import { ccService } from "@cc-api";

import { ReportFilter, Severity } from "@cc/report-server-types";
import { SeverityIcon } from "@/components/Icons";
import { SeverityMixin } from "@/mixins";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "SeverityFilter",
  components: {
    SelectOption,
    SeverityIcon
  },
  mixins: [ BaseSelectOptionFilterMixin, SeverityMixin ],

  data() {
    return {
      id: "severity"
    };
  },

  methods: {
    encodeValue(severityId) {
      return this.severityFromCodeToString(severityId);
    },

    decodeValue(severityName) {
      return this.severityFromStringToCode(severityName);
    },

    updateReportFilter() {
      this.setReportFilter({
        severity: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "severity") return;
      this.update();
    },

    fetchItems() {
      this.loading = true;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.severity = null;

      ccService.getClient().getSeverityCounts(this.runIds, reportFilter,
        this.cmpData, (err, res) => {
          this.items = Object.keys(Severity).map(status => {
            const severityId = Severity[status];
            return {
              id: severityId,
              title: this.encodeValue(severityId),
              count: res[severityId] !== undefined ? res[severityId] : 0
            };
          });
          this.updateSelectedItems();
          this.loading = false;
        });
    }
  }
};
</script>
