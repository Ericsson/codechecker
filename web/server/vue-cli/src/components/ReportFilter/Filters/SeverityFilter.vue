<template>
  <select-option
    title="Severity"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
  >
    <template v-slot:icon="{ item }">
      <severity-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
import { ccService } from '@cc-api';

import { Severity } from "@cc/report-server-types";
import { SeverityIcon } from "@/components/icons";
import { SeverityMixin } from "@/mixins";

import SelectOption from './SelectOption/SelectOption';
import BaseSelectOptionFilter from './BaseSelectOptionFilter';

export default {
  name: 'SeverityFilter',
  components: {
    SelectOption,
    SeverityIcon
  },
  extends: BaseSelectOptionFilter,
  mixins: [ SeverityMixin ],

  props: {
    reportFilter: { type: Object, required: true }
  },

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
      return this.severityFromStringToCode(severityName)
    },

    updateReportFilter() {
      this.reportFilter.severity = this.selectedItems.map(item => item.id);
    },

    fetchItems() {
      this.loading = true;

      const runIds = null;
      const reportFilter = null;
      const cmpData = null;

      ccService.getClient().getSeverityCounts(runIds, reportFilter, cmpData,
      (err, res) => {
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
}
</script>
