<template>
  <v-icon
    v-if="currentStatus"
    :color="currentStatus.color"
    :title="currentStatus.title"
    :size="size"
    :icon="currentStatus.icon"
  />
</template>

<script setup>
import { computed } from "vue";
import { ReviewStatus } from "@cc/report-server-types";;

const props = defineProps({
  status: { type: Number, required: true },
  size: { type: String, default: "24" }
});

const reviewStatusInfo = {
  [ReviewStatus.UNREVIEWED]: {
    color: "var(--color-soft-blue)",
    title: "Unreviewed",
    icon: "mdi-eye-off"
  },
  [ReviewStatus.CONFIRMED]: {
    color: "var(--color-soft-red)",
    title: "Confirmed",
    icon: "mdi-check-circle-outline"
  },
  [ReviewStatus.FALSE_POSITIVE]: {
    color: "var(--color-gray-light)",
    title: "False positive",
    icon: "mdi-cancel"
  },
  [ReviewStatus.INTENTIONAL]: {
    color: "var(--color-soft-green)",
    title: "Intentional",
    icon: "mdi-close-circle-outline"
  }
};

const currentStatus = computed(function() {
  return reviewStatusInfo[parseInt(props.status)];
});
</script>
