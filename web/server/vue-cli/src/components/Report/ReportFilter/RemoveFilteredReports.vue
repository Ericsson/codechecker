<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="600px"
    cancel-btn-color="primary"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    title="Remove filtered results"
    @confirm="confirmDelete"
  >
    <template v-slot:activator="{ props }">
      <v-btn
        v-bind="props"
        variant="outlined"
        color="error"
      >
        <v-icon left>
          mdi-delete
        </v-icon>
        Remove Filtered Reports
      </v-btn>
    </template>

    <template v-slot:content>
      Are you sure you want to remove all filtered results?
    </template>
  </ConfirmDialog>
</template>

<script setup>
import ConfirmDialog from "@/components/ConfirmDialog";
import { useBaseFilter } from "@/composables/useBaseFilter";
import { ccService, handleThriftError } from "@cc-api";
import { ref } from "vue";

const emit = defineEmits([ "update" ]);
const baseFilter = useBaseFilter();
const dialog = ref(false);

function confirmDelete() {
  ccService.getClient().removeRunReports(
    baseFilter.runIds,
    baseFilter.reportFilter,
    baseFilter.cmpData,
    handleThriftError(() => {
      emit("update");
      dialog.value = false;
    }));
}
</script>
