<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="edit-review-status-rule-dialog"
    scrollable
    :title="dialogTitle"
    @confirm="saveReviewStatusRule"
  >
    <template v-slot:content>
      <v-form ref="form">
        <v-text-field
          v-model.trim="reportHash"
          class="report-hash mb-2"
          label="Report hash*"
          autofocus
          variant="outlined"
          required
          :hide-details="true"
          :rules="rules.reportHash"
        />

        <select-review-status
          v-model="status"
          class="mb-2"
          label="Select review status*"
          :clearable="false"
          :rules="rules.selectReviewStatus"
        />

        <v-textarea
          v-model.trim="message"
          class="message pa-0"
          variant="outlined"
          name="reviewStatusMessage"
          label="(Optionally) Explain the status change..."
          :hide-details="true"
        />
      </v-form>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, ref, watch } from "vue";

import { ConfirmDialog } from "@/components";
import SelectReviewStatus from "./SelectReviewStatus";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  rule: { type: Object, default: () => null },
});
const emit = defineEmits([
  "update:modelValue",
  "on:confirm"
]);
const reportHash = ref(null);
const status = ref(null);
const message = ref(null);
const rules = ref({
  reportHash: [ v => !!v || "Report hash is required" ],
  selectReviewStatus: [ v => !!v || "Review status is required" ],
});
const form = ref(null);

const dialog = computed({
  get() {
    return props.modelValue;
  },
  set(val) {
    emit("update:modelValue", val);
  }
});

const dialogTitle = computed(() => {
  return props.rule ? "Edit review status rule" : "New review status rule";
});

watch(dialog, newVal => {
  if (newVal) {
    form.value?.resetValidation();
  }
});

watch(() => props.rule, newRule => {
  reportHash.value = newRule?.reportHash;
  status.value = newRule?.status;
  message.value = newRule?.message;
});

async function saveReviewStatusRule() {
  const { valid } = await form.value.validate();
  if (!valid) return;

  ccService.getClient().addReviewStatusRule(
    reportHash.value,
    status.value,
    message.value,
    handleThriftError(async () => {
      emit("on:confirm");
      dialog.value = false;
    }));
}
</script>
