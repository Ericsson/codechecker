<template>
  <select-option
    title="Review Status"
    :items="items"
  >
    <template v-slot:icon="{ item }">
      <review-status-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
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
      items: [
        { id: ReviewStatus.UNREVIEWED, title: 'Unreviewed', count: 3 },
        { id: ReviewStatus.CONFIRMED, title: 'Confirmed', count: 7 },
        { id: ReviewStatus.FALSE_POSITIVE, title: 'False positive', count: 0 },
        { id: ReviewStatus.INTENTIONAL, title: 'Intentional', count: 10 },
      ]
    };
  }
}
</script>
