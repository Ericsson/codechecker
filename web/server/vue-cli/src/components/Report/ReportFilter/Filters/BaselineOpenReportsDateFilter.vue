<template>
  <filter-toolbar
    :id="id"
    title="Open Reports Date"
    @clear="clear(true)"
  >
    <template v-slot:append-toolbar-title>
      <v-tooltip max-width="300" right>
        <template v-slot:activator="{ on }">
          <v-icon
            color="accent"
            class="ml-1"
            small
            v-on="on"
          >
            mdi-help-circle
          </v-icon>
        </template>
        <span>
          Filter reports that were <i>DETECTED BEFORE</i> the given date and
          <i>NOT FIXED BEFORE</i> the given date.<br><br>

          The <i>detection date</i> of a report is the <i>storage date</i> when
          the report was stored to the server for the first time and the
          <i>fix date</i> is the date when the report is <i>dissappeared</i>
          from a storage.
        </span>
      </v-tooltip>

      <span
        v-if="selectedDateTitle"
        class="selected-items"
        :title="selectedDateTitle"
      >
        ({{ selectedDateTitle }})
      </span>
    </template>

    <v-card-actions>
      <date-time-picker
        :input-class="id"
        :dialog-class="id"
        :value="date"
        label="Report date"
        @input="setDateTime"
      />
    </v-card-actions>
  </filter-toolbar>
</template>

<script>
import DateMixin from "@/mixins/date.mixin";
import DateTimePicker from "@/components/DateTimePicker";

import BaseFilterMixin from "./BaseFilter.mixin";
import FilterToolbar from "./Layout/FilterToolbar";

export default {
  name: "BaselineOpenReportsDateFilter",
  components: {
    DateTimePicker,
    FilterToolbar
  },
  mixins: [ BaseFilterMixin, DateMixin ],

  data() {
    return {
      id: "open-reports-date",
      date: null
    };
  },

  computed: {
    selectedDateTitle() {
      return this.date ? this.dateTimeToStr(this.date) : null;
    }
  },

  methods: {
    setDateTime(date, updateUrl=true) {
      this.date = date;
      this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    updateReportFilter() {
      this.setReportFilter({
        openReportsDate: this.date ? this.getUnixTime(this.date) : null
      });
    },

    getUrlState() {
      return {
        [ this.id ]: this.date ? this.dateTimeToStr(this.date) : undefined
      };
    },

    initByUrl() {
      const date = this.$route.query[this.id];
      if (date) {
        const dateTime = new Date(date);

        // We need to round the date upward because we will send the dates
        // to the server without milliseconds.
        if (dateTime.getMilliseconds()) {
          dateTime.setMilliseconds(1000);
        }

        this.setDateTime(dateTime, false);
      }
    },

    clear(updateUrl) {
      this.setDateTime(null, updateUrl);
    }
  }
};
</script>
