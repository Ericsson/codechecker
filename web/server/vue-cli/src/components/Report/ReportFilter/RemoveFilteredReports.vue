<template>
  <confirm-dialog
    v-model="dialog"
    max-width="600px"
    cancel-btn-color="primary"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    @confirm="confirmDelete"
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

    <template v-slot:title>
      Remove filtered resutlts
    </template>

    <template v-slot:content>
      Are you sure you want to remove all filtered results?
    </template>
  </confirm-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import ConfirmDialog from "@/components/ConfirmDialog";
import BaseFilterMixin from "./Filters/BaseFilter.mixin";

export default {
  name: "RemoveFileteredReports",
  components: {
    ConfirmDialog
  },
  mixins: [ BaseFilterMixin ],
  data() {
    return {
      dialog: false
    };
  },

  methods: {
    confirmDelete() {
      ccService.getClient().removeRunReports(this.runIds, this.reportFilter,
        this.cmpData, handleThriftError(() => {
          this.$emit("update");
          this.dialog = false;
        }));
    }
  }
};
</script>
