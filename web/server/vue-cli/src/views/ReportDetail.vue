<template>
  <v-container :fluid="true">
    <v-row>
      <v-col>
        <report-tree />
      </v-col>
      <v-col cols="9">
        <report />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import VContainer from "Vuetify/VGrid/VContainer";
import VRow from "Vuetify/VGrid/VRow";
import VCol from "Vuetify/VGrid/VCol";

import Report from '@/components/Report';
import ReportTree from '@/components/ReportTree/ReportTree';

export default {
  name: 'ReportDetail',
  components: {
    VContainer, VRow, VCol,
    Report,
    ReportTree
  }
}
</script>
