<template>
  <v-btn
    id="clear-all-filter-btn"
    outlined
    text
    color="primary"
    @click="clearAllFilters"
  >
    <v-icon left>
      mdi-delete
    </v-icon>
    Clear All Filters
  </v-btn>
</template>

<script>
import { BaseFilterMixin } from "./Filters";

export default {
  name: "ClearAllFilters",
  mixins: [ BaseFilterMixin ],

  methods: {
    clearAllFilters() {
      this.$emit("clear");
    }
  }
};
</script>
