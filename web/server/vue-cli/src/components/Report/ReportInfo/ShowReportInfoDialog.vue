<template>
  <v-dialog
    v-model="dialog"
    content-class="report-info-dialog"
    max-width="600px"
  >
    <template v-slot:activator="{ on }">
      <v-row>
        <v-col
          cols="auto"
          class="pa-0 mx-4"
        >
          <slot :on="on" />
        </v-col>
      </v-row>
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Report info

        <v-spacer />

        <v-btn class="close-btn" icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <report-info :value="value" />
        </v-container>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import ReportInfo from "./ReportInfo";

export default {
  name: "ShowReportInfoDialog",
  components: { ReportInfo },
  props: {
    value: { type: Object, default: null }
  },
  data() {
    return {
      dialog: false
    };
  }
};
</script>
