<template>
  <v-card flat>
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

import BaseFilterMixin from './BaseFilter.mixin';

export default {
  name: 'ReportHashFilter',
  components: {
    VTextField, VCard, VCardActions,
    VToolbar, VToolbarTitle, VToolbarItems, VSpacer, VBtn, VIcon
  },
  mixins: [ BaseFilterMixin ],

  data() {
    return {
      id: 'report-hash',
      reportHash: null
    };
  },
  watch: {
    reportHash: function () {
      this.updateUrl();
      this.updateReportFilter();
    }
  },

  methods: {
    updateReportFilter() {
      this.reportFilter.reportHash =
        this.reportHash ? [ `${this.reportHash}*` ] : null;
    },

    getUrlState() {
      return {
        [this.id]: this.reportHash
      };
    },

    initByUrl() {
      return new Promise((resolve) => {
        const state = this.$route.query[this.id];
        if (state) {
          this.reportHash = state;
        }

        resolve();
      });
    },
  }
}
</script>
