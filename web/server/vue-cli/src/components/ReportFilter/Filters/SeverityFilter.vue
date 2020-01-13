<template>
  <select-option
    title="Severity"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
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

import SelectOption from './SelectOption/SelectOption';

export default {
  name: 'SeverityFilter',
  components: {
    SelectOption,
    SeverityIcon
  },
  data() {
    return {
      selected: [],
      items: [],
      loading: false
    };
  },

  methods: {
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
            title: status,
            count: res[severityId] !== undefined ? res[severityId] : 0
          };
        });
        this.loading = false;
      });
    }
  }
}
</script>
