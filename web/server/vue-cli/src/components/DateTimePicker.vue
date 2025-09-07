<template>
  <v-dialog
    v-model="dialog"
    :content-class="dialogClass"
    width="400"
  >
    <template #activator="{ props }">
      <v-text-field
        v-bind="props"
        :label="label"
        :class="[inputClass, 'pa-0', 'ma-0']"
        :prepend-inner-icon="prependInnerIcon"
        :outlined="outlined"
        :density="dense ? 'compact' : undefined"
        hide-details
        readonly
      >
        <template #append>
          <slot name="append" />
        </template>
      </v-text-field>
    </template>

    <v-card>
      <v-card-text class="pa-0">
        <v-tabs v-model="activeTab" grow>
          <v-tab>
            <v-icon>mdi-calendar</v-icon>
          </v-tab>
          <v-tab :disabled="!date">
            <v-icon>mdi-clock-outline</v-icon>
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <v-window-item>
            <v-date-picker
              v-model="date"
              show-adjacent-months
              color="primary"
              @update:model-value="activeTab = 1"
            />
          </v-window-item>
          <v-window-item>
            <v-time-picker
              v-model="time"
              format="24hr"
              full-width
              with-seconds
              color="primary"
            />
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="grey lighten-1"
          variant="text"
          @click="clear"
        >
          Clear
        </v-btn>
        <v-btn
          color="green darken-1"
          variant="text"
          @click="ok"
        >
          OK
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { format, parse } from "date-fns";

export default {
  name: "DateTimePicker",
  props: {
    value: { type: [Date, String], default: null },
    label: { type: String, default: "" },
    dateFormat: { type: String, default: "yyyy-MM-dd" },
    timeFormat: { type: String, default: "HH:mm:ss" },
    defaultTime: { type: String, default: "00:00:00" },
    inputClass: { type: String, default: null },
    dialogClass: { type: String, default: null },
    outlined: { type: Boolean, default: false },
    dense: { type: Boolean, default: false },
    prependInnerIcon: { type: String, default: null }
  },
  data() {
    return {
      dialog: false,
      activeTab: 0,
      date: null,
      time: this.defaultTime
    };
  },
  computed: {
    dateTimeFormat() {
      return `${this.dateFormat} ${this.timeFormat}`;
    },
    dateTime() {

      let hours, minutes;
      [hours,minutes] = this.time.split(":");
      const formatted = new Date(this.date);
      formatted.setHours(parseInt(hours));
      formatted.setMinutes(parseInt(minutes));
      return formatted;
    },
    formattedDatetime() {
      return this.dateTime ? format(this.dateTime, this.dateTimeFormat) : null;
    }
  },
  watch: {
    value: {
      handler() {
        this.init();
      },
      immediate: true
    }
  },
  methods: {
    init() {
      if (!this.value) {
        this.resetDateTimes();
        return;
      }

      let initValue = null;
      if (this.value instanceof Date) {
        initValue = this.value;
      } else if (typeof this.value === "string") {
        try {
          initValue = parse(this.value, this.dateTimeFormat, new Date());
        } catch (e) {
          initValue = null;
        }
      }

      if (initValue) {
        this.date = format(initValue, this.dateFormat);
        this.time = format(initValue, this.timeFormat);
      } else {
        this.resetDateTimes();
      }
    },
    clear() {
      this.reset();
      this.resetDateTimes();
      this.$emit("input", null);
    },
    ok() {
      this.reset();
      this.$emit("input", this.dateTime);
    },
    reset() {
      this.dialog = false;
      this.activeTab = 0;
    },
    resetDateTimes() {
      this.date = null;
      this.time = this.defaultTime;
    }
  }
};
</script>

<style scoped>
.v-picker {
  box-shadow: none;
}
</style>
