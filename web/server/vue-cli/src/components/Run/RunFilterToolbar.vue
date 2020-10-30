<template>
  <v-toolbar flat class="run-filter-toolbar mb-4">
    <v-row>
      <v-col align-self="center">
        <v-text-field
          :value="runName"
          class="run-name"
          prepend-inner-icon="mdi-magnify"
          label="Search for runs..."
          single-line
          hide-details
          outlined
          solo
          flat
          dense
          @input="setRunName"
        />
      </v-col>

      <v-col align-self="center">
        <v-text-field
          :value="runTag"
          class="run-tag"
          prepend-inner-icon="mdi-tag"
          label="Filter events by tag name..."
          clearable
          single-line
          hide-details
          outlined
          solo
          flat
          dense
          @input="setRunTag"
        >
          <template #append>
            <tooltip-help-icon>
              Filter run history events by the given tag name.<br>
              <i>Note</i>: this will filter only the history events.
            </tooltip-help-icon>
          </template>
        </v-text-field>
      </v-col>

      <v-col align-self="center" width="50px">
        <date-time-picker
          :value="storedAfter"
          input-class="stored-after"
          dialog-class="stored-after"
          label="History stored after..."
          prepend-inner-icon="mdi-calendar-arrow-right"
          outlined
          dense
          @input="setStoredAfter"
        >
          <template #append>
            <tooltip-help-icon>
              Filter run history events that were stored after the given
              date.<br>
              <i>Note</i>: this will filter only the history events.
            </tooltip-help-icon>
          </template>
        </date-time-picker>
      </v-col>

      <v-col align-self="center" cols="2">
        <date-time-picker
          :value="storedBefore"
          input-class="stored-before"
          dialog-class="stored-before"
          label="History stored before..."
          prepend-inner-icon="mdi-calendar-arrow-left"
          outlined
          dense
          @input="setStoredBefore"
        >
          <template #append>
            <tooltip-help-icon>
              Filter run history events that were stored before the given
              date.<br>
              <i>Note</i>: this will filter only the history events.
            </tooltip-help-icon>
          </template>
        </date-time-picker>
      </v-col>

      <v-spacer />

      <v-col align="right">
        <delete-run-btn
          :selected="selected"
          @on-confirm="update"
        />

        <v-btn
          outlined
          color="primary"
          class="diff-runs-btn mr-2"
          :to="diffTargetRoute"
          :disabled="isDiffBtnDisabled"
        >
          <v-icon left>
            mdi-select-compare
          </v-icon>
          Diff
        </v-btn>

        <v-btn
          icon
          class="reload-runs-btn"
          title="Reload runs"
          color="primary"
          @click="update"
        >
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
      </v-col>
    </v-row>
  </v-toolbar>
</template>

<script>
import _ from "lodash";
import { mapGetters, mapMutations } from "vuex";
import {
  SET_RUN_HISTORY_RUN_TAG,
  SET_RUN_HISTORY_STORED_AFTER,
  SET_RUN_HISTORY_STORED_BEFORE,
  SET_RUN_NAME
} from "@/store/mutations.type";

import { DateMixin } from "@/mixins";
import DateTimePicker from "@/components/DateTimePicker";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { DeleteRunBtn } from "@/components/Run";

export default {
  name: "RunFilter",
  components: {
    DateTimePicker,
    DeleteRunBtn,
    TooltipHelpIcon
  },
  mixins: [ DateMixin ],
  props: {
    selected: { type: Array, required: true },
    selectedBaselineRuns: { type: Array, required: true },
    selectedBaselineTags: { type: Array, required: true },
    selectedComparedToRuns: { type: Array, required: true },
    selectedComparedToTags: { type: Array, required: true }
  },

  computed: {
    ...mapGetters("run", [
      "runName",
      "runTag",
      "storedBefore",
      "storedAfter",
    ]),

    isDiffBtnDisabled() {
      return (!this.selectedBaselineRuns.length &&
              !this.selectedBaselineTags.length) ||
             (!this.selectedComparedToRuns.length &&
              !this.selectedComparedToTags.length);
    },

    diffTargetRoute() {
      return {
        name: "reports",
        query: {
          ...this.$router.currentRoute.query,
          "run": this.selectedBaselineRuns.length
            ? this.selectedBaselineRuns : undefined,
          "run-tag": this.selectedBaselineTags.length
            ? this.selectedBaselineTags : undefined,
          "newcheck": this.selectedComparedToRuns.length
            ? this.selectedComparedToRuns : undefined,
          "run-tag-newcheck": this.selectedComparedToTags.length
            ? this.selectedComparedToTags : undefined,
        }
      };
    },
  },

  created() {
    // Initalize the URLs.
    this.initByUrl();

    // Watch for filter changes.
    this.$watch("runName", _.debounce(() => {
      const runName = this.runName ? this.runName : undefined;
      this.updateUrl({ "run": runName });

      this.$emit("on-run-filter-changed");
    }, 500));

    this.$watch("runTag", _.debounce(() => {
      const runTag = this.runTag ? this.runTag : undefined;
      this.updateUrl({ "run-tag": runTag });

      this.$emit("on-run-history-filter-changed");
    }, 500));

    this.$watch("storedAfter", _.debounce(() => {
      const date = this.storedAfter
        ? this.dateTimeToStr(this.storedAfter) : undefined;
      this.updateUrl({ "stored-after": date });

      this.$emit("on-run-history-filter-changed");
    }, 500));

    this.$watch("storedBefore", _.debounce(() => {
      const date = this.storedBefore
        ? this.dateTimeToStr(this.storedBefore) : undefined;
      this.updateUrl({ "stored-before": date });

      this.$emit("on-run-history-filter-changed");
    }, 500));
  },

  methods: {
    ...mapMutations("run", [
      SET_RUN_NAME,
      SET_RUN_HISTORY_RUN_TAG,
      SET_RUN_HISTORY_STORED_BEFORE,
      SET_RUN_HISTORY_STORED_AFTER
    ]),

    initByUrl() {
      const runName = this.$router.currentRoute.query["run"];
      if (runName)
        this.setRunName(runName);

      const runTag = this.$router.currentRoute.query["run-tag"];
      if (runTag)
        this.setRunTag(runTag);

      const storedAfter = this.$router.currentRoute.query["stored-after"];
      if (storedAfter)
        this.setStoredAfter(new Date(storedAfter));

      const storedBefore = this.$router.currentRoute.query["stored-before"];
      if (storedBefore)
        this.setStoredBefore(new Date(storedBefore));
    },

    updateUrl(params) {
      this.$router.replace({
        query: {
          ...this.$route.query,
          ...params
        }
      }).catch(() => {});
    },

    update() {
      this.$emit("update");
    }
  }
};
</script>
