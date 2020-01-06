<template>
  <v-footer color="secondary" padless>
    <v-row justify="center" no-gutters>
      <v-col
        class="py-4 text-center white--text"
        cols="12"
      >
        {{ new Date().getFullYear() }} — <strong>Ericsson</strong>
      </v-col>
    </v-row>
  </v-footer>
</template>

<script>
import { VFooter } from "Vuetify/VFooter";
import VRow from "Vuetify/VGrid/VRow";
import VCol from "Vuetify/VGrid/VCol";

export default {
  name: "TheHeader",
  components: {
    VFooter, VCol, VRow
  }
};
</script>
