<template>
  <v-checkbox
    :input-value="isUnique"
    @change="setIsUnique"
  >
    <template v-slot:label>
      Unique reports
      <v-tooltip max-width="200" right>
        <template v-slot:activator="{ on }">
          <v-icon
            color="accent"
            class="ml-1"
            v-on="on"
          >
            mdi-help-circle
          </v-icon>
        </template>
        <span>
          This narrows the report list to unique bug. The same bug may appear
          several times if it is found on different control paths, i.e. through
          different function calls. By checking <b>Unique reports</b> a report
          appears only once even if it is found on several paths.
        </span>
      </v-tooltip>
    </template>
  </v-checkbox>
</template>

<script>
import BaseFilterMixin from "./BaseFilter.mixin";

export default {
  name: "UniqueFilter",
  mixins: [ BaseFilterMixin ],

  data() {
    return {
      id: "is-unique",
      defaultValue: false
    };
  },

  computed: {
    isUnique() {
      return !!this.$store.state.report.reportFilter.isUnique;
    }
  },

  methods: {
    setIsUnique(isUnique, updateUrl=true) {
      this.setReportFilter({ isUnique: isUnique });
      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    encodeValue(isUnique) {
      return isUnique ? "on" : "off";
    },

    decodeValue(state) {
      return state === "off" ? false : true;
    },

    getUrlState() {
      return {
        [this.id]: this.encodeValue(this.isUnique)
      };
    },

    initByUrl() {
      return new Promise(resolve => {
        const state = this.$route.query[this.id];
        if (state) {
          const isUnique = this.decodeValue(state);
          this.setIsUnique(isUnique, false);
        } else {
          this.setIsUnique(this.defaultValue, false);
        }

        resolve();
      });
    },

    clear(updateUrl) {
      this.setIsUnique(this.defaultValue, updateUrl);
    }
  }
};
</script>
