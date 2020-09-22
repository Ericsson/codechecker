<template>
  <v-dialog
    v-model="dialog"
    :content-class="dialogClass"
    width="400"
  >
    <template v-slot:activator="{ on }">
      <v-text-field
        :label="label"
        :value="formattedDatetime"
        :class="[ inputClass, 'pa-0', 'ma-0' ]"
        :prepend-inner-icon="prependInnerIcon"
        :outlined="outlined"
        :dense="dense"
        hide-details
        readonly
        v-on="on"
      >
        <template #append>
          <slot name="append" />
        </template>
      </v-text-field>
    </template>

    <v-card>
      <v-card-text class="pa-0">
        <v-tabs
          v-model="activeTab"
          fixed-tabs
        >
          <v-tab>
            <v-icon>mdi-calendar</v-icon>
          </v-tab>

          <v-tab
            :disabled="!date"
          >
            <v-icon>mdi-clock-outline</v-icon>
          </v-tab>

          <v-tab-item>
            <v-date-picker
              v-model="date"
              full-width
              @input="activeTab = 1"
            />
          </v-tab-item>

          <v-tab-item>
            <v-time-picker
              v-model="time"
              full-width
              use-seconds
              format="24hr"
            />
          </v-tab-item>
        </v-tabs>
      </v-card-text>

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="grey lighten-1"
          class="clear-btn"
          text
          @click.native="clear"
        >
          Clear
        </v-btn>

        <v-btn
          class="ok-btn"
          color="green darken-1"
          text
          @click="ok"
        >
          Ok
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
    value: { type: [ Date, String ], default: null },
    label: { type: String, default: "" },
    dateFormat: { type: String, default: "yyyy-MM-dd" },
    timeFormat: { type: String, default: "HH:mm:ss" },
    defaultTime: { type: String, default: "00:00:00" },
    inputClass: { type: String, default: null },
    dialogClass: { type: String, default: null },
    outlined: { type: Boolean, default: false },
    dense: { type: Boolean, default: false },
    prependInnerIcon: { type: String, default: null },
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
      if (this.date && this.time) {
        const dt = this.date + " " + this.time;
        return parse(dt, this.dateTimeFormat, new Date());
      }

      return null;
    },

    formattedDatetime() {
      return this.dateTime ? format(this.dateTime, this.dateTimeFormat) : null;
    }
  },

  watch: {
    value() {
      this.init();
    }
  },

  mounted() {
    this.init();
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
      } else if (typeof this.value === "string" ||
                 this.value instanceof String
      ) {
        initValue = parse(this.value, this.dateTimeFormat, new Date());
      }

      this.date = format(initValue, this.dateFormat);
      this.time = format(initValue, this.timeFormat);
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

<style lang="scss" scoped>
::v-deep .v-picker.v-card {
  box-shadow: none;

  & > .v-picker__title {
    border-radius: 0;
  }
}

</style>
