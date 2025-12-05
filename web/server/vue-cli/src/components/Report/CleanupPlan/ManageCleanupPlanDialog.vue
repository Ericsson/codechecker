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

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        <v-container>
          <v-row>
            <h1>Manage Cleanup Plans</h1>
            <span
              class="subtitle-1"
            >
              Use cleanup plans to track progress of reports in your product.
            </span>
          </v-row>
        </v-container>

        <v-spacer />

        <v-btn
          class="close-btn"
          icon="mdi-close"
          @click="dialog = false"
        />
      </v-card-title>

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
  value: { type: Boolean, default: false },
});

const emit = defineEmits([ "update:value" ]);

const dialog = computed({
  get: () => props.value,
  set: val => emit("update:value", val)
});
</script>