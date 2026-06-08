<template>
  <select-option
    :id="id"
    title="Severity"
    :bus="bus"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <severity-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

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

      return new Promise(resolve => {
        ccService.getClient().getSeverityCounts(this.runIds, reportFilter,
          this.cmpData, handleThriftError(res => {
            resolve(Object.keys(Severity).map(status => {
              const severityId = Severity[status];
              const count =
                res[severityId] !== undefined ? res[severityId].toNumber() : 0;

              return {
                id: severityId,
                title: this.encodeValue(severityId),
                count: count
              };
            }));
            this.loading = false;
          }));
      });
    }
  }
};
</script>
