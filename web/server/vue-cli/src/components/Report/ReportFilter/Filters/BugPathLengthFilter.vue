<template>
  <filter-toolbar
    title="Bug path length"
    :panel="panel"
    @clear="clear(true)"
  >
    <template v-slot:append-toolbar-title>
      <span
        v-if="selectedBugPathLengthTitle"
        class="selected-items"
        :title="selectedBugPathLengthTitle"
      >
        ({{ selectedBugPathLengthTitle }})
      </span>
    </template>

    <v-form ref="form">
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
            <v-text-field
              :id="minId"
              :value="minBugPathLength"
              :rules="rules.bugPathLength"
              label="Min..."
              @input="setMinBugPathLength"
            />
          </v-col>

          <v-col
            cols="12"
            sm="6"
            md="6"
            class="py-0"
          >
            <v-text-field
              :id="maxId"
              :value="maxBugPathLength"
              :rules="rules.bugPathLength"
              label="Max..."
              @input="setMaxBugPathLength"
            />
          </v-col>
        </v-row>
      </v-container>
    </v-form>
  </filter-toolbar>
</template>

<script>
import { BugPathLengthRange } from "@cc/report-server-types";

import BaseFilterMixin from "./BaseFilter.mixin";
import FilterToolbar from "./Layout/FilterToolbar";

export default {
  name: "BugPathLengthFilter",
  components: {
    FilterToolbar
  },
  mixins: [ BaseFilterMixin ],
  data() {
    return {
      minId: "min-bug-path-length",
      maxId: "max-bug-path-length",
      minBugPathLength: null,
      maxBugPathLength: null,
      rules: {
        bugPathLength: [
          v => (!v || !!v && !isNaN(parseInt(v))) || "Number is required"
        ]
      },
    };
  },

  computed: {
    selectedBugPathLengthTitle() {
      return [
        ...(this.minBugPathLength ? [ `min: ${this.minBugPathLength}` ]: []),
        ...(this.maxBugPathLength ? [ `max: ${this.maxBugPathLength}` ]: [])
      ].join(", ");
    }
  },

  methods: {
    setMinBugPathLength(bugPathLength, updateUrl=true) {
      if (this.$refs.form && !this.$refs.form.validate()) return;

      this.minBugPathLength = bugPathLength;
      this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    setMaxBugPathLength(bugPathLength, updateUrl=true) {
      if (this.$refs.form && !this.$refs.form.validate()) return;

      this.maxBugPathLength = bugPathLength;
      this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    getUrlState() {
      return {
        [this.minId]: this.minBugPathLength || undefined,
        [this.maxId]: this.maxBugPathLength || undefined
      };
    },

    initByUrl() {
      return new Promise(resolve => {
        const minBugPathLength = this.$route.query[this.minId];
        if (parseInt(minBugPathLength)) {
          this.setMinBugPathLength(minBugPathLength, false);
        }

        const maxBugPathLength = this.$route.query[this.maxId];
        if (parseInt(maxBugPathLength)) {
          this.setMaxBugPathLength(maxBugPathLength, false);
        }

        resolve();
      });
    },

    initPanel() {
      this.panel = this.minBugPathLength !== null ||
        this.maxBugPathLength !== null;
    },

    updateReportFilter() {
      let bugPathLength = null;

      if (this.minBugPathLength || this.maxBugPathLength)  {
        bugPathLength = new BugPathLengthRange({
          min : this.minBugPathLength ? this.minBugPathLength : null,
          max : this.maxBugPathLength ? this.maxBugPathLength : null,
        });
      }

      this.setReportFilter({ bugPathLength: bugPathLength });
    },

    clear(updateUrl) {
      this.setMinBugPathLength(null, false);
      this.setMaxBugPathLength(null, false);

      if (updateUrl) {
        this.$emit("update:url");
      }
    }
  }
};
</script>
