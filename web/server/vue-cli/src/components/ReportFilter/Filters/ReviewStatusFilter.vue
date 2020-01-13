<template>
  <select-option
    title="Review Status"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
  >
    <template v-slot:icon="{ item }">
      <review-status-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
import { ccService } from '@cc-api';

import { ReviewStatus } from "@cc/report-server-types";
import { ReviewStatusIcon } from "@/components/icons";

import SelectOption from './SelectOption/SelectOption';

export default {
  name: 'ReviewStatusFilter',
  components: {
    SelectOption,
    ReviewStatusIcon
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

      ccService.getClient().getReviewStatusCounts(runIds, reportFilter, cmpData,
      (err, res) => {
        this.items = Object.keys(ReviewStatus).map(status => {
          const reviewStatusId = ReviewStatus[status];
          return {
            id: reviewStatusId,
            title: status,
            count: res[reviewStatusId] !== undefined ? res[reviewStatusId] : 0
          };
        });
        this.loading = false;
      });
    }
  }
}
</script>
