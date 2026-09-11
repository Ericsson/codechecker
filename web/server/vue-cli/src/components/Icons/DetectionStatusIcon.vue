<template>
  <v-icon
    v-if="status === DetectionStatus.NEW"
    color="var(--color-soft-red)"
    :title="formattedTitle"
    :size="size"
  >
    mdi-alert-decagram
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.RESOLVED"
    color="var(--color-soft-green)"
    :title="formattedTitle"
    :size="size"
  >
    mdi-check-circle
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNRESOLVED"
    color="var(--color-soft-blue)"
    :title="formattedTitle"
    :size="size"
  >
    mdi-bug
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.REOPENED"
    color="var(--color-red)"
    :title="formattedTitle"
    :size="size"
  >
    mdi-restore
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.OFF"
    color="var(--color-gray-light)"
    :title="formattedTitle"
    :size="size"
  >
    mdi-power
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNAVAILABLE"
    color="var(--color-grey)"
    :title="formattedTitle"
    :size="size"
  >
    mdi-close
  </v-icon>
</template>

<script setup>
import { useDetectionStatus } from "@/composables/useDetectionStatus";
import { DetectionStatus } from "@cc/report-server-types";
import { computed } from "vue";

const props = defineProps({
  status: { type: Number, required: true },
  size: { type: Number, default: undefined },
  title: { type: String, default: null }
});

const detectionStatus = useDetectionStatus();

const formattedTitle = computed(() => 
  props.title || detectionStatus.detectionStatusFromCodeToString(props.status)
);
</script>
