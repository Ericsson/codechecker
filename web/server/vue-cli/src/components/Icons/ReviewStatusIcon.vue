<template>
  <v-icon
    v-if="status === ReviewStatus.UNREVIEWED"
    color="#4b9fd5"
    title="Unreviewed"
    :size="size"
    icon="mdi-eye-off"
  />

  <v-icon
    v-else-if="status === ReviewStatus.CONFIRMED"
    color="#e92625"
    title="Confirmed"
    :size="size"
    icon="mdi-check-circle-outline"
  />

  <v-icon
    v-else-if="status === ReviewStatus.FALSE_POSITIVE"
    color="#808080"
    title="False positive"
    :size="size"
    icon="mdi-cancel"
  />

  <v-icon
    v-else-if="status === ReviewStatus.INTENTIONAL"
    color="#669603"
    title="Intentional"
    :size="size"
    icon="mdi-close-circle-outline"
  />
</template>

<script setup>
import { ReviewStatus } from "@cc/report-server-types";

defineProps({
  status: { type: Number, required: true },
  size: { type: Number, default: undefined }
});
</script>
