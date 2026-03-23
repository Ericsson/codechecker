<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="edit-cleanup-plan-dialog"
    max-width="600px"
    scrollable
    :title="title"
    @confirm="saveCleanupPlan"
    @cancel="resetValues"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        color="primary"
        class="new-cleanup-plan-btn"
        variant="outlined"
      >
        New
      </v-btn>
    </template>

    <template v-slot:content>
      <v-container>
        <v-form ref="form">
          <v-text-field
            v-model.trim="name"
            class="cleanup-plan-name"
            label="Name*"
            autofocus
            variant="outlined"
            required
            :rules="rules.name"
          />

          <due-date-menu
            v-model="dueDate"
          />

          <v-textarea
            v-model.trim="description"
            class="cleanup-plan-description "
            label="Description"
            variant="outlined"
          />
        </v-form>
      </v-container>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, ref, watch } from "vue";

import ConfirmDialog from "@/components/ConfirmDialog";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  cleanupPlan: { type: Object, default: () => null }
});

const emit = defineEmits([
  "save:cleanup-plan",
  "update:modelValue"
]);

const form = ref(null);

const description = ref(null);
const dueDate = ref(null);
const name = ref(null);
const dueDateMenu = ref(false);
const rules = ref({
  name: [ v => !!v || "Name is required" ],
  value: [
    v => !!v || "Value is required"
  ]
});

const dialog = computed({
  get: () => props.modelValue,
  set: val => emit("update:modelValue", val)
});

const title = computed(
  () => props.cleanupPlan ? "Edit cleanup plan" : "New cleanup plan"
);

watch(dialog, () => {
  if (!dialog.value) return;

  description.value = props.cleanupPlan?.description || null;
  dueDate.value = props.cleanupPlan?.dueDate?.toNumber() || null;
  name.value = props.cleanupPlan?.name || null;
});

async function saveCleanupPlan() {
  if (!form.value.validate()) return;

  if (props.cleanupPlan) {
    // Edit an existing cleanup plan.
    ccService.getClient().updateCleanupPlan(
      props.cleanupPlan.id, name.value,
      description.value, dueDate.value,
      handleThriftError(async success => {
        if (success) {
          emit("save:cleanup-plan");
          dialog.value = false;
        }
      }));
  } else {
    // Add new cleanup plan.
    ccService.getClient().addCleanupPlan(
      name.value, description.value, dueDate.value,
      handleThriftError(async () => {
        emit("save:cleanup-plan");
        dialog.value = false;
      }));
  }
}
</script>

<style lang="scss">
.value textarea::placeholder {
  opacity: 0.5;
}
</style>
