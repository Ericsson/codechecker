<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="600px"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        color="error"
        class="mr-2"
        outlined
        :disabled="!selected.length"
        v-on="on"
      >
        <v-icon left>
          mdi-trash-can-outline
        </v-icon>
        Delete
      </v-btn>
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Confirm deletion of runs

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          Are you sure? The following runs will be removed:
          <v-chip
            v-for="item in selected"
            :key="item.name"
            outlined
            color="error"
            class="mr-2 mb-2"
          >
            {{ item.name }}
          </v-chip>
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
import { RunFilter } from "@cc/report-server-types";

export default {
  name: "DeleteRunBtn",
  props: {
    selected: { type: Array, required: true }
  },
  data() {
    return {
      dialog: false
    };
  },

  methods: {
    confirmDelete() {
      const runFilter = new RunFilter({
        ids: this.selected.map((run) => run.runId)
      });

      ccService.getClient().removeRun(null, runFilter, () => {
        this.selected.splice(0, this.selected.length);
        this.dialog = false;

        this.$emit("on-confirm");
      });
    }
  }
}
</script>
