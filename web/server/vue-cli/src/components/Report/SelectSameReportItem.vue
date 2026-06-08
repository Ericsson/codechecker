<template>
  <div>
    <detection-status-icon
      :status="item.detectionStatus"
      :size="16"
    />
    <review-status-icon
      :status="item.reviewStatus"
      :size="16"
    />
    {{ item.runName }}:{{ item.fileName }}:L{{ item.line }}
    <v-chip
      :color="bugPathLenColor.getBugPathLenColor(item.bugPathLength)"
      label
      light
      size="small"
    >
      {{ item.bugPathLength }}
    </v-chip>
  </div>
</template>

<script setup>
import { DetectionStatusIcon, ReviewStatusIcon } from "@/components/Icons";
import { useBugPathLenColor } from "@/composables/useBugPathLenColor";

defineProps({
  item: { type: Object, required: true }
});

const bugPathLenColor = useBugPathLenColor();

</script>
