<template>
  <div>
    <v-avatar
      left
      :size="16"
    >
      <review-status-icon
        :status="item.id"
        :size="16"
      />
    </v-avatar>
    {{ item.label }}
  </div>
</template>

<script>
import { ReviewStatusIcon } from "@/components/Icons";

export default {
  name: "SelectSameReportItem",
  components: {
    ReviewStatusIcon
  },
  props: {
    item: { type: Object, required: true }
  }
};
</script>
