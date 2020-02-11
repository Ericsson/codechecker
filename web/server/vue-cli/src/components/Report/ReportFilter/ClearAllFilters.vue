<template>
  <v-btn
    @click="clearAllFilters"
  >
    <v-icon>mdi-delete</v-icon>
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
      console.log("Clear All Filters");
    }
  }
}
</script>
