<template>
  <v-checkbox
    class="ma-0 py-0"
    :hide-details="true"
    :input-value="isUnique"
    @change="setIsUnique"
  >
    <template v-slot:label>
      Unique reports
      <tooltip-help-icon>
        This narrows the report list to unique bug. The same bug may appear
        several times if it is found on different control paths, i.e. through
        different function calls or in different runs. By checking
        <b>Unique reports</b>, a report appears only once even if it is found
        on several paths or in different runs.
      </tooltip-help-icon>
    </template>
  </v-checkbox>
</template>

<script>
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import BaseFilterMixin from "./BaseFilter.mixin";

export default {
  name: "UniqueFilter",
  components: { TooltipHelpIcon },
  mixins: [ BaseFilterMixin ],
  data() {
    return {
      id: "is-unique",
      defaultValue: false
    };
  },

  computed: {
    isUnique() {
      return !!this.$store.state[this.namespace].reportFilter.isUnique;
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
      return state === "on" ? true : false;
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
