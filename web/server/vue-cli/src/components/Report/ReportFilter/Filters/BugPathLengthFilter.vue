<template>
  <filter-toolbar
    title="Bug path length"
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
          <v-text-field
            v-model="minBugPathLength"
            label="Min..."
            :hide-details="true"
          />
        </v-col>

        <v-col
          cols="12"
          sm="6"
          md="6"
          class="py-0"
        >
          <v-text-field
            v-model="maxBugPathLength"
            label="Max..."
            :hide-details="true"
          />
        </v-col>
      </v-row>
    </v-container>
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
      maxBugPathLength: null
    };
  },

  watch: {
    minBugPathLength() {
      this.onBugPathLengthChange();
    },

    maxBugPathLength() {
      this.onBugPathLengthChange();
    }
  },

  methods: {
    getUrlState() {
      return {
        [this.minId]: this.minBugPathLength || undefined,
        [this.maxId]: this.maxBugPathLength || undefined
      };
    },

    initByUrl() {
      return new Promise((resolve) => {
        const minBugPathLength = this.$route.query[this.minId];
        if (minBugPathLength) {
          this.minBugPathLength = minBugPathLength;
        }

        const maxBugPathLength = this.$route.query[this.maxId];
        if (maxBugPathLength) {
          this.maxBugPathLength = maxBugPathLength;
        }

        resolve();
      });
    },

    onBugPathLengthChange() {
      let bugPathLength = null;

      if (this.minBugPathLength || this.maxBugPathLength)  {
        bugPathLength = new BugPathLengthRange({
          min : this.minBugPathLength ? this.minBugPathLength : null,
          max : this.maxBugPathLength ? this.maxBugPathLength : null,
        });
      }

      this.setReportFilter({ bugPathLength: bugPathLength });
      this.updateUrl();
    },

    clear() {
      this.minBugPathLength = null;
      this.maxBugPathLength = null;
    }
  }
}
</script>
