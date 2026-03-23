<template>
  <v-dialog
    v-model="dialog"
    content-class="manage-cleanup-plan-dialog"
    max-width="600px"
    transition="dialog-bottom-transition"
    fullscreen
    hide-overlay
    scrollable
  >
    <template v-slot:activator="{}">
      <slot />
    </template>

    <v-card
      title="Manage Cleanup Plans"
      subtitle="Use cleanup plans to track progress of reports in your product."
    >
      <template v-slot:append>
        <v-btn
          class="close-btn"
          icon="mdi-close"
          size="small"
          @click="dialog = false"
        />
      </template>

      <v-card-text class="pa-0">
        <v-container>
          <list-cleanup-plans />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="error"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from "vue";
import ListCleanupPlans from "./ListCleanupPlans";

const props = defineProps({
  modelValue: { type: Boolean, default: false }
});

const emit = defineEmits([ "update:modelValue" ]);

const dialog = computed({
  get() {
    return props.modelValue;
  },
  set(value) {
    emit("update:modelValue", value);
  }
});
</script>