<template>
  <v-avatar
    rounded="xs"
    :color="color"
    :size="size"
    :title="severityInfo[status].title"
  >
    <span class="text-white text-weight-bold">
      {{ severityInfo[status].letter }}
    </span>
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

const severityInfo = {
  [Severity.UNSPECIFIED]: { letter: "U", title: "Unspecified" },
  [Severity.STYLE]: { letter: "S", title: "Style" },
  [Severity.LOW]: { letter: "L", title: "Low" },
  [Severity.MEDIUM]: { letter: "M", title: "Medium" },
  [Severity.HIGH]: { letter: "H", title: "High" },
  [Severity.CRITICAL]: { letter: "C", title: "Critical" },
};
</script>
