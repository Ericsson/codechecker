<template>
  <filter-toolbar
    title="Detection date"
    @clear="clear"
  >
    <v-container
      class="py-0"
    >
      <v-row>
        <v-col
          cols="12"
          sm="6"
          md="6"
          class="py-0"
        >
          <date-time-picker
            v-model="fromDateTime"
            label="Detection date"
          />
        </v-col>

        <v-col
          cols="12"
          sm="6"
          md="6"
          class="py-0"
        >
          <date-time-picker
            v-model="toDateTime"
            label="Fix date"
          />
        </v-col>
      </v-row>
    </v-container>
  </filter-toolbar>
</template>

<script>
import { format } from "date-fns";

import DateTimePicker from "@/components/DateTimePicker";
import BaseFilterMixin from "./BaseFilter.mixin";
import FilterToolbar from "./Layout/FilterToolbar";

export default {
  name: "DetectionDateFilter",
  components: {
    DateTimePicker,
    FilterToolbar
  },
  mixins: [ BaseFilterMixin ],
  data() {
    return {
      fromDateTimeId: "first-detection-date",
      toDateTimeId: "fix-date",
      fromDateTime: null,
      toDateTime: null
    };
  },

  watch: {
    fromDateTime() {
      this.onDetectionDateChange();
    },

    toDateTime() {
      this.onDetectionDateChange();
    }
  },

  methods: {
    getUrlState() {
      const state = {};

      state[this.fromDateTimeId] = this.fromDateTime
        ? this.dateTimeToStr(this.fromDateTime) : undefined;

      state[this.toDateTimeId] = this.toDateTime
        ? this.dateTimeToStr(this.toDateTime) : undefined;

      return state;
    },

    initByUrl() {
      return new Promise(resolve => {
        const fromDateTime = this.$route.query[this.fromDateTimeId];
        if (fromDateTime) {
          this.fromDateTime = new Date(fromDateTime);
        }

        const toDateTime = this.$route.query[this.toDateTimeId];
        if (toDateTime) {
          this.toDateTime = new Date(toDateTime);
        }

        resolve();
      });
    },

    onDetectionDateChange() {
      const detectionDate = {};

      if (this.fromDateTime)  {
        detectionDate.firstDetectionDate = this.getTimeStamp(this.fromDateTime);
      }

      if (this.toDateTime)  {
        detectionDate.fixDate = this.getTimeStamp(this.toDateTime);
      }

      if (Object.keys(detectionDate).length) {
        this.setReportFilter(detectionDate);
      }

      this.updateUrl();
    },

    dateTimeToStr(date) {
      return format(date, "yyyy-MM-dd HH:mm:ss", new Date());
    },

    // Returns UTC timestamp of the parameter.
    getTimeStamp(dateTime) {
      return dateTime ? this.dateToUTCTime(dateTime) / 1000 : null;
    },

    // Converts a date to an UTC format timestamp.
    dateToUTCTime(date) {
      return Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate(),
        date.getUTCHours(),
        date.getUTCMinutes(),
        date.getUTCSeconds(),
        date.getUTCMilliseconds());
    },

    clear() {
      // TODO: this will not work.
      // see: https://github.com/darrenfang/vuetify-datetime-picker/pull/51
      this.fromDateTime = null;
      this.toDateTime = null;
    }
  }
};
</script>
