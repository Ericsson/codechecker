<template>
  <v-btn>
    <v-icon>mdi-delete</v-icon>
    Clear All Filters
  </v-btn>
</template>

<script>
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";

export default {
  name: 'ClearAllFilters',
  components: {
    VBtn, VIcon
  }
}
</script>
