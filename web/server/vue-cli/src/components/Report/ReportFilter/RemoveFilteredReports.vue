<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="600px"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        outlined
        color="error"
        v-on="on"
      >
        <v-icon left>
          mdi-delete
        </v-icon>
        Remove Filtered Reports
      </v-btn>
    </template>

    <v-card>
      <v-card-title
        class="headline error white--text"
        primary-title
      >
        Remove filtered resutlts

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          Are you sure you want to remove all filtered results?
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          color="error"
          text
          @click="confirmDelete"
        >
          Remove
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ccService } from "@cc-api";

export default {
  name: "RemoveFileteredReports",
  data() {
    return {
      dialog: false
    };
  },

  methods: {
    confirmDelete() {
      ccService.getClient().removeRunReports(this.runIds, this.reportFilter,
        this.cmpData, (/* err, res */) => {
          this.$emit("update");
          this.dialog = false;
        });
    }
  }
};
</script>
