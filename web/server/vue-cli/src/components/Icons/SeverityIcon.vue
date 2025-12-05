<template>
  <v-avatar
    v-if="status === Severity.UNSPECIFIED"
    rounded="xs"
    :color="color"
    :size="size"
    title="Unspecified"
  >
    <span class="text-white text-weight-bold">U</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.STYLE"
    rounded="xs"
    :color="color"
    :size="size"
    title="Style"
  >
    <span class="text-white text-weight-bold">S</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.LOW"
    rounded="xs"
    :color="color"
    :size="size"
    title="Low"
  >
    <span class="text-white text-weight-bold">L</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.MEDIUM"
    rounded="xs"
    :color="color"
    :size="size"
    title="Medium"
  >
    <span class="text-white text-weight-bold">M</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.HIGH"
    rounded="xs"
    :color="color"
    :size="size"
    title="High"
  >
    <span class="text-white text-weight-bold">H</span>
  </v-avatar>

  <v-avatar
    v-else-if="status === Severity.CRITICAL"
    rounded="xs"
    :color="color"
    :size="size"
    title="Critical"
  >
    <span class="text-white text-weight-bold">C</span>
  </v-avatar>
</template>

<script setup>
import { useSeverity } from "@/composables/useSeverity";
import { Severity } from "@cc/report-server-types";
import { computed } from "vue";

const props = defineProps({
  status: { type: Number, required: true },
  size: { type: Number, default: 24 }
});

const severity = useSeverity();

const color = computed(() => severity.severityFromCodeToColor(props.status));
</script>
