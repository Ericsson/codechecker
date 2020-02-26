<template>
  <filter-toolbar
    title="Detection date"
    @clear="clear(true)"
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
            :value="fromDateTime"
            label="Detection date"
            @input="setFromDateTime"
          />
        </v-col>

        <v-col
          cols="12"
          sm="6"
          md="6"
          class="py-0"
        >
          <date-time-picker
            :value="toDateTime"
            label="Fix date"
            @input="setToDateTime"
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


  methods: {
    setFromDateTime(dateTime, updateUrl=true) {
      this.fromDateTime = dateTime;
      this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    setToDateTime(dateTime, updateUrl=true) {
      this.toDateTime = dateTime;
      this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

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
          this.setFromDateTime(new Date(fromDateTime), false);
        }

        const toDateTime = this.$route.query[this.toDateTimeId];
        if (toDateTime) {
          this.setToDateTime(new Date(toDateTime), false);
        }

        resolve();
      });
    },

    updateReportFilter() {
      const firstDetectionDate = this.fromDateTime
        ? this.getTimeStamp(this.fromDateTime) : null;
      const fixDate = this.toDateTime
        ? this.getTimeStamp(this.toDateTime) : null;

      this.setReportFilter({
        firstDetectionDate: firstDetectionDate,
        fixDate: fixDate
      });
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

    clear(updateUrl) {
      this.setFromDateTime(null, false);
      this.setToDateTime(null, false);

      if (updateUrl) {
        this.$emit("update:url");
      }
    }
  }
};
</script>
