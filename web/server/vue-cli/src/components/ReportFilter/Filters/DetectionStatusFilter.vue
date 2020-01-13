<template>
  <select-option
    title="Detection status"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
  >
    <template v-slot:icon="{ item }">
      <detection-status-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
import { ccService } from '@cc-api';

import { DetectionStatus } from "@cc/report-server-types";
import { DetectionStatusIcon } from "@/components/icons";

import SelectOption from './SelectOption/SelectOption';

export default {
  name: 'DetectionStatusFilter',
  components: {
    SelectOption,
    DetectionStatusIcon
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

      ccService.getClient().getDetectionStatusCounts(runIds, reportFilter,
      cmpData, (err, res) => {
        this.items = Object.keys(DetectionStatus).map(status => {
          const id = DetectionStatus[status];
          return {
            id: id,
            title: status,
            count: res[id] !== undefined ? res[id] : 0
          };
        });
        this.loading = false;
      });
    }
  }
}
</script>
