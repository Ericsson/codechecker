<template>
  <select-option
    :title="title"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :loading="loading"
    :multiple="false"
    :panel="panel"
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
            :label="fromDateTimeLabel"
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
            :label="toDateTimeLabel"
            @input="setToDateTime"
          />
        </v-col>
      </v-row>
    </v-container>
  </select-option>
</template>

<script>
import { DateInterval, ReportDate } from "@cc/report-server-types";

import DateTimePicker from "@/components/DateTimePicker";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";
import DateMixin from "@/mixins/date.mixin";
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
  mixins: [ BaseSelectOptionFilterMixin, DateMixin ],
  data() {
    return {
      title: "Detection date",
      fromDateTimeId: "detected-after",
      toDateTimeId: "detected-before",
      fromDateTimeLabel: "Detected after...",
      toDateTimeLabel: "Detected before...",
      fromDateTime: null,
      toDateTime: null,
      filterFieldName: "detected"
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

    initPanel() {
      this.panel = this.fromDateTime !== null || this.toDateTime !== null;
    },

    updateReportFilter() {
      const date = new ReportDate(this.reportFilter.date);
      if (this.fromDateTime || this.toDateTime) {
        if (!date[this.filterFieldName])
          date[this.filterFieldName] = new DateInterval();

        date[this.filterFieldName].before = this.toDateTime
          ? this.getUnixTime(this.toDateTime) : null;
        date[this.filterFieldName].after = this.fromDateTime
          ? this.getUnixTime(this.fromDateTime) : null;
      } else if (date) {
        date[this.filterFieldName] = null;
      }

      this.setReportFilter({ date: date });
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
