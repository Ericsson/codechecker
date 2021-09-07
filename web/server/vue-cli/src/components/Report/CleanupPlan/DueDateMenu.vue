<template>
  <v-menu
    v-model="menu"
    :close-on-content-click="false"
    :nudge-right="40"
    transition="scale-transition"
    offset-y
    min-width="auto"
  >
    <template v-slot:activator="{ on, attrs }">
      <v-text-field
        :value="date"
        label="Due date"
        append-icon="mdi-calendar"
        readonly
        outlined
        v-bind="attrs"
        v-on="on"
      />
    </template>

    <v-date-picker v-model="date" />
  </v-menu>
</template>

<script>
import { format, fromUnixTime, getUnixTime, parse } from "date-fns";

export default {
  name: "DueDateMenu",
  props: {
    value: { type: Number, default: null },
  },
  data() {
    return {
      menu: false,
      format: "yyyy-MM-dd"
    };
  },
  computed: {
    date: {
      get() {
        return this.value
          ? format(fromUnixTime(this.value), this.format, new Date)
          : null;
      },
      set(val) {
        this.$emit("update:value",
          val ? getUnixTime(parse(val, this.format, new Date)) : null);

        this.menu = false;
      }
    }
  }
};
</script>
