<template>
  <v-dialog
    v-model="dialogVisible"
    content-class="manage-source-component-dialog"
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
      title="Manage source components"
    >
      <template v-slot:append>
        <v-btn
          class="close-btn"
          icon="mdi-close"
          @click="dialogVisible = false"
        />
      </template>

      <v-card-text class="pa-0">
        <v-container>
          <list-source-components />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="error"
          text
          @click="dialogVisible = false"
        >
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from "vue";
import ListSourceComponents from "./ListSourceComponents";

const props = defineProps({ modelValue: Boolean });
const emit = defineEmits([ "update:modelValue" ]);

const dialogVisible = computed({
  get: () => props.modelValue,
  set: val => emit("update:modelValue", val),
});

</script>