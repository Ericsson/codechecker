<template>
  <confirm-dialog
    v-model="dialog"
    content-class="delete-run-dialog"
    max-width="600px"
    cancel-btn-color="primary"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    :confirm-in-progress="removingInProgress"
    @confirm="confirmDelete"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        color="error"
        class="delete-run-btn mr-2"
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

    <template v-slot:title>
      Confirm deletion of runs
    </template>

    <template v-slot:content>
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
    </template>
  </confirm-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { RunFilter } from "@cc/report-server-types";

import ConfirmDialog from "@/components/ConfirmDialog";

export default {
  name: "DeleteRunBtn",
  components: {
    ConfirmDialog
  },
  props: {
    selected: { type: Array, required: true }
  },
  data() {
    return {
      dialog: false,
      removingInProgress: false,
    };
  },

  methods: {
    confirmDelete() {
      this.removingInProgress = true;

      const runFilter = new RunFilter({
        ids: this.selected.map(run => run.runId)
      });

      ccService.getClient().removeRun(null, runFilter,
        handleThriftError(() => {
          this.selected.splice(0, this.selected.length);
          this.dialog = false;

          this.$emit("on-confirm");
          this.removingInProgres = false;
        }));
    }
  }
};
</script>
