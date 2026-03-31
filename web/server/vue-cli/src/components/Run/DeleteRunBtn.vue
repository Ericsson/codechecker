<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="delete-run-dialog"
    max-width="600px"
    cancel-btn-color="primary"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    :confirm-in-progress="removingInProgress"
    title="Confirm deletion of runs"
    @confirm="confirmDelete"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        color="error"
        class="delete-run-btn mr-2"
        :variant="variant"
        :disabled="!selected.length"
      >
        <v-icon left>
          mdi-trash-can-outline
        </v-icon>
        Delete
      </v-btn>
    </template>

    <template v-slot:content>
      Are you sure? The following runs will be removed:
      <v-chip
        v-for="item in selected"
        :key="item.name"
        variant="outlined"
        color="error"
        class="mr-2 mb-2"
      >
        {{ item.name }}
      </v-chip>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { RunFilter } from "@cc/report-server-types";
import { ref } from "vue";

import ConfirmDialog from "@/components/ConfirmDialog";

const props = defineProps({
  selected: { type: Array, required: true },
  variant: { type: String, default: "solo" }
});

const emit = defineEmits([ "on-confirm", "delete-complete" ]);

const dialog = ref(false);
const removingInProgress = ref(false);

function confirmDelete() {
  removingInProgress.value = true;

  const _runFilter = new RunFilter({
    ids: props.selected.map(run => run.runId)
  });

  ccService.getClient().removeRun(null, _runFilter,
    handleThriftError(() => {
      dialog.value = false;

      emit("on-confirm");
      emit("delete-complete");
      removingInProgress.value = false;
    }));
}
</script>
