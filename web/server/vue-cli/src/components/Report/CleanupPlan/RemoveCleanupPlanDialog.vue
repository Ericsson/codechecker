<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="600px"
    cancel-btn-color="primary"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    content-class="remove-cleanup-plan-dialog"
    title="Remove cleanup plan"
    @confirm="removeCleanupPlan"
  >
    <template v-if="cleanupPlan" v-slot:content>
      Are you sure that you would like to remove
      <b>{{ cleanupPlan.name }}</b> cleanup plan?
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed } from "vue";

import ConfirmDialog from "@/components/ConfirmDialog";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  cleanupPlan: { type: Object, default: () => null }
});

const emit = defineEmits([ "update:modelValue", "on:confirm" ]);

const dialog = computed({
  get() {
    return props.modelValue;
  },
  set(val) {
    emit("update:modelValue", val);
  }
});

function removeCleanupPlan() {
  ccService.getClient().removeCleanupPlan(props.cleanupPlan.id,
    handleThriftError(success => {
      if (success) {
        emit("on:confirm");
        dialog.value = false;
      }
    }));
}
</script>
