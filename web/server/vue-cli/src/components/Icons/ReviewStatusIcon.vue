<template>
  <v-icon
    v-if="status === ReviewStatus.UNREVIEWED"
    :color="reviewStatus.reviewStatusColor(ReviewStatus.UNREVIEWED)"
    title="Unreviewed"
    :size="size"
    icon="mdi-eye-off"
  />

  <v-icon
    v-else-if="status === ReviewStatus.CONFIRMED"
    :color="reviewStatus.reviewStatusColor(ReviewStatus.CONFIRMED)"
    title="Confirmed"
    :size="size"
    icon="mdi-check-circle-outline"
  />

  <v-icon
    v-else-if="status === ReviewStatus.FALSE_POSITIVE"
    :color="reviewStatus.reviewStatusColor(ReviewStatus.FALSE_POSITIVE)"
    title="False positive"
    :size="size"
    icon="mdi-cancel"
  />

  <v-icon
    v-else-if="status === ReviewStatus.INTENTIONAL"
    :color="reviewStatus.reviewStatusColor(ReviewStatus.INTENTIONAL)"
    title="Intentional"
    :size="size"
    icon="mdi-close-circle-outline"
  />
</template>

<script setup>
import { ReviewStatus } from "@cc/report-server-types";
import { useReviewStatus } from "@/composables/useReviewStatus";

defineProps({
  status: { type: Number, required: true },
  size: { type: Number, default: undefined }
});

const reviewStatus = useReviewStatus();
</script>
