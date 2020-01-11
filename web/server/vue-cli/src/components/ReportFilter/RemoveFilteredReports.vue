<template>
  <v-btn outlined color="error">
    <v-icon>mdi-delete</v-icon>
    Remove Filtered Reports
  </v-btn>
</template>

<script>
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";

export default {
  name: 'RemoveFileteredReports',
  components: {
    VBtn, VIcon
  }
}
</script>
