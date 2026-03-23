<template>
  <v-icon
    v-if="status === ReviewStatus.UNREVIEWED"
    color="#4b9fd5"
    title="Unreviewed"
    :size="size"
  >
    mdi-eye-off
  </v-icon>

  <v-icon
    v-else-if="status === ReviewStatus.CONFIRMED"
    color="#e92625"
    title="Confirmed"
    :size="size"
  >
    mdi-check-circle-outline
  </v-icon>

  <v-icon
    v-else-if="status === ReviewStatus.FALSE_POSITIVE"
    color="#808080"
    title="False positive"
    :size="size"
  >
    mdi-cancel
  </v-icon>

  <v-icon
    v-else-if="status === ReviewStatus.INTENTIONAL"
    color="#669603"
    title="Intentional"
    :size="size"
  >
    mdi-close-circle-outline
  </v-icon>
</template>

<script setup>
import { ReviewStatus } from "@cc/report-server-types";

defineProps({
  status: { type: Number, required: true },
  size: { type: Number, default: null }
});
</script>
