<template>
  <filter-toolbar
    :id="id"
    title="Outstanding reports on a given date"
    :panel="panel"
    @clear="clear(true)"
  >
    <template v-slot:append-toolbar-title>
      <tooltip-help-icon>
        Filter reports that were <i>DETECTED BEFORE</i> the given date and
        <i>NOT FIXED BEFORE</i> the given date.<br><br>

        The <i>detection date</i> of a report is the <i>storage date</i> when
        the report was stored to the server for the first time and the
        <i>fix date</i> is the date when the report is <i>dissappeared</i>
        from a storage.
      </tooltip-help-icon>

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
import TooltipHelpIcon from "@/components/TooltipHelpIcon";

import BaseFilterMixin from "./BaseFilter.mixin";
import FilterToolbar from "./Layout/FilterToolbar";

export default {
  name: "BaselineOpenReportsDateFilter",
  components: {
    DateTimePicker,
    FilterToolbar,
    TooltipHelpIcon
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

    initPanel() {
      this.panel = this.date !== null;
    },

    clear(updateUrl) {
      this.setDateTime(null, updateUrl);
    }
  }
};
</script>
