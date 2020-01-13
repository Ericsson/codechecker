<template>
  <v-card>
    <v-toolbar flat>
      <v-toolbar-title>Report hash filter</v-toolbar-title>
      <v-spacer />
      <v-toolbar-items>
        <v-btn icon>
          <v-icon>mdi-delete</v-icon>
        </v-btn>
      </v-toolbar-items>
    </v-toolbar>

    <v-card-actions class="">
      <v-text-field
        v-model="reportHash"
        append-icon="mdi-magnify"
        label="Search for report hash (min 5 characters)..."
        single-line
        hide-details
        outlined
        solo
        clearable
        flat
        dense
      />
    </v-card-actions>
  </v-card>
</template>

<script>
import VTextField from "Vuetify/VTextField/VTextField";
import { VCard, VCardActions } from "Vuetify/VCard";
import { VToolbar, VToolbarTitle, VToolbarItems } from "Vuetify/VToolbar";
import VSpacer from "Vuetify/VGrid/VSpacer";
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";

export default {
  name: 'ReportHashFilter',
  components: {
    VTextField, VCard, VCardActions,
    VToolbar, VToolbarTitle, VToolbarItems, VSpacer, VBtn, VIcon
  },
  props: {
    reportFilter: { type: Object, required: true }
  },
  data() {
    return {
      reportHash: null
    };
  },
  watch: {
    reportHash: function (val) {
      this.reportFilter.reportHash = val ? [ `${val}*` ] : null;
    }
  }
}
</script>
