<template>
  <div class="d-inline-flex align-center">
    <review-status-icon
      :status="value"
      :size="16"
      class="mr-2"
    />

    <slot name="label">
      {{ label }}
    </slot>
  </div>
</template>

<script setup>
import { ReviewStatusIcon } from "@/components/Icons";
import { useReviewStatus } from "@/composables/useReviewStatus";
import { computed } from "vue";

const props = defineProps({
  value: { type: Number, required: true }
});

const reviewStatus = useReviewStatus();

const label = computed(function() {
  return reviewStatus.reviewStatusFromCodeToString(props.value);
});
</script>
