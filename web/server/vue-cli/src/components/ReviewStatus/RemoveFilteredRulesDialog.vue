<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="remove-filtered-rules-dialog"
    confirm-btn-label="Remove"
    title="Remove filtered review status rules"
    @confirm="removeReviewStatusRule"
  >
    <template v-slot:content>
      <v-container>
        <v-alert
          class="mt-2"
          color="error"
          border="start"
          elevation="2"
          colored-border
          icon="mdi-alert-outline"
        >
          Are you sure that you would like to remove all the filtered review
          status rules (<b>{{ total }}</b>) from the database?
          <br><br>
          <b>IMPORTANT**</b>: be careful when you delete rules because this
          operation can not be undone.
        </v-alert>
      </v-container>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed } from "vue";

import { ConfirmDialog } from "@/components";

const props = defineProps({
  value: { type: Boolean, default: false },
  filter: { type: Object, default: null },
  total: { type: Number, default: null },
});

const emit = defineEmits([ "update:value", "on:confirm" ]);

const dialog = computed({
  get() {
    return props.value;
  },
  set(val) {
    emit("update:value", val);
  }
});

function removeReviewStatusRule() {
  ccService.getClient().removeReviewStatusRules(props.filter,
    handleThriftError(success => {
      if (success) {
        emit("on:confirm", props.rule);
        dialog.value = false;
      }
    }));
}
</script>
