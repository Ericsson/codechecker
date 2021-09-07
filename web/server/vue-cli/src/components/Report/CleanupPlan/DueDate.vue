<template>
  <span :class="{ 'red--text': expired, 'font-weight-bold': expired }">
    <span v-if="expired">
      <v-icon small color="red">
        mdi-alert-outline
      </v-icon>
      Past due by
    </span>

    <span v-else-if="!hideLabel">
      <v-icon small>
        mdi-calendar-blank
      </v-icon>
      Due by
    </span>

    {{ dueDate }}
  </span>
</template>

<script>
import { fromUnixTime as fromUnixTimestamp, startOfToday } from "date-fns";
import fromUnixTime from "@/filters/from-unix-time";

export default {
  name: "DueDate",
  props: {
    value: { type: Object, required: true },
    hideLabel: { type: Boolean, default: false }
  },
  computed: {
    dueDate() {
      return fromUnixTime(this.value, "yyyy-MM-dd");
    },
    expired() {
      return startOfToday() > fromUnixTimestamp(this.value);
    }
  }
};
</script>
