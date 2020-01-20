<template>
  <v-btn
    @click="clearAllFilters"
  >
    <v-icon>mdi-delete</v-icon>
    Clear All Filters
  </v-btn>
</template>

<script>
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";

import { BaseFilterMixin } from './Filters';

export default {
  name: 'ClearAllFilters',
  components: {
    VBtn, VIcon
  },
  mixins: [ BaseFilterMixin ],

  methods: {
    clearAllFilters() {
      console.log("Clear All Filters");
    }
  }
}
</script>
