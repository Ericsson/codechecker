<template>
  <select-option
    title="Detection date"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :loading="loading"
    :multiple="false"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <detection-date-filter-icon :value="item.id" />
    </template>

    <template v-slot:append-toolbar-title>
      <span
        v-if="selectedDetectionDateTitle"
        class="selected-items"
        :title="selectedDetectionDateTitle"
      >
        ({{ selectedDetectionDateTitle }})
      </span>
    </template>

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
            :input-class="fromDateTimeId"
            :dialog-class="fromDateTimeId"
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
            :input-class="toDateTimeId"
            :dialog-class="toDateTimeId"
            :value="toDateTime"
            label="Fix date"
            @input="setToDateTime"
          />
        </v-col>
      </v-row>
    </v-container>
  </select-option>
</template>

<script>
import { format } from "date-fns";

import DateTimePicker from "@/components/DateTimePicker";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";
import SelectOption from "./SelectOption/SelectOption";
import DetectionDateFilterItems, {
  getDateInterval,
  titleFormatter
} from "./DetectionDateFilterItems";
import DetectionDateFilterIcon from "./DetectionDateFilterIcon";

export default {
  name: "DetectionDateFilter",
  components: {
    DateTimePicker,
    DetectionDateFilterIcon,
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],
  data() {
    return {
      fromDateTimeId: "first-detection-date",
      toDateTimeId: "fix-date",
      fromDateTime: null,
      toDateTime: null
    };
  },

  computed: {
    selectedDetectionDateTitle() {
      return [
        ...(this.fromDateTime
          ? [ `after: ${this.dateTimeToStr(this.fromDateTime)}` ]: []),
        ...(this.toDateTime
          ? [ `before: ${this.dateTimeToStr(this.toDateTime)}` ]: [])
      ].join(", ");
    }
  },

  methods: {
    setSelectedItems(selectedItems/*, updateUrl=true*/) {
      this.selectedItems = selectedItems;
      const interval = getDateInterval(selectedItems[0].id);

      this.setFromDateTime(interval.from, false);
      this.setToDateTime(interval.to, false);

      this.$emit("update:url");
    },

    setFromDateTime(dateTime, updateUrl=true) {
      this.fromDateTime = dateTime;
      this.updateReportFilter();

      if (updateUrl) {
        this.selectedItems = [];
        this.$emit("update:url");
      }
    },

    setToDateTime(dateTime, updateUrl=true) {
      this.toDateTime = dateTime;
      this.updateReportFilter();

      if (updateUrl) {
        this.selectedItems = [];
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
          const dateTime = new Date(toDateTime);

          // We need to round the date upward because we will send the dates
          // to the server without milliseconds.
          if (dateTime.getMilliseconds()) {
            dateTime.setMilliseconds(1000);
          }

          this.setToDateTime(dateTime, false);
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

    fetchItems() {
      return Object.keys(DetectionDateFilterItems).map(key => {
        const id = DetectionDateFilterItems[key];

        return {
          id: id,
          title: titleFormatter(id)
        };
      });
    },

    dateTimeToStr(date) {
      return format(date, "yyyy-MM-dd HH:mm:ss", new Date());
    },

    // Returns UTC timestamp of the parameter.
    getTimeStamp(dateTime) {
      return dateTime ? parseInt(this.dateToUTCTime(dateTime) / 1000) : null;
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
      this.selectedItems = [];

      if (updateUrl) {
        this.$emit("update:url");
      }
    }
  }
};
</script>
