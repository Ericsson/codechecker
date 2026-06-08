<template>
  <span :class="{ 'red--text': expired, 'font-weight-bold': expired }">
    <span v-if="expired">
      <v-icon
        size="small"
        color="red"
      >
        mdi-alert-outline
      </v-icon>
      Past due by
    </span>

    <span v-else-if="!hideLabel">
      <v-icon
        size="small"
      >
        mdi-calendar-blank
      </v-icon>
      Due by
    </span>

    {{ dueDate }}
  </span>
</template>

<script setup>
import fromUnixTime from "@/filters/from-unix-time";
import { fromUnixTime as fromUnixTimestamp, startOfToday } from "date-fns";
import { computed } from "vue";

const props = defineProps({
  value: { type: Number, required: true },
  hideLabel: { type: Boolean, default: false }
});

const dueDate = computed(() => {
  return fromUnixTime(props.value, "yyyy-MM-dd");
});

const expired = computed(() => {
  return startOfToday() > fromUnixTimestamp(props.value);
});
</script>
