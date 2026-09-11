<template>
  <v-chip
    v-if="type === 'macro' || type === 'note'"
    :color="color"
    rounded="0"
    size="small"
  >
    <span class="text-weight-bold text-white">{{ index }}</span>
  </v-chip>

  <v-avatar
    v-else
    :color="color"
    :size="size"
  >
    <span class="text-caption text-white">{{ index }}</span>
  </v-avatar>
</template>

<script setup>
import { computed } from "vue";
import { getCssColor } from "@/utilities/colors";

const props = defineProps({
  type: { type: String, default: null },
  index: { type: [ Number, String ], default: null },
  size: { type: Number, default: 24 }
});

const color = computed(() => {
  switch (props.type) {
  case "error":
    return getCssColor("color-report-step-message-error");
  case "fixit":
    return getCssColor("color-report-step-message-fixit");
  case "macro":
    return getCssColor("color-report-step-message-macro");
  case "note":
    return getCssColor("color-report-step-message-note");
  default:
    return getCssColor("color-report-step-message-default");
  }
});
</script>
