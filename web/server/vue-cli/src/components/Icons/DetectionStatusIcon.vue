<template>
  <v-icon
    v-if="status === DetectionStatus.NEW"
    color="#ec7672"
    :title="formattedTitle"
    :size="size"
  >
    mdi-alert-decagram
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.RESOLVED"
    color="#669603"
    :title="formattedTitle"
    :size="size"
  >
    mdi-check
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNRESOLVED"
    color="#007ea7"
    :title="formattedTitle"
    :size="size"
  >
    mdi-bug
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.REOPENED"
    color="#ff0000"
    :title="formattedTitle"
    :size="size"
  >
    mdi-restore
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.OFF"
    color="#4e4e4e"
    :title="formattedTitle"
    :size="size"
  >
    mdi-power
  </v-icon>

  <v-icon
    v-else-if="status === DetectionStatus.UNAVAILABLE"
    color="#737373"
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
  size: { type: String, default: undefined },
  title: { type: String, default: null }
});

const detectionStatus = useDetectionStatus();

const formattedTitle = computed(() => 
  props.title || detectionStatus.detectionStatusFromCodeToString(props.status)
);
</script>
