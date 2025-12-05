<template>
  <v-dialog
    v-model="dialog"
    content-class="remove-source-component-dialog"
    max-width="600px"
    scrollable
  >
    <template v-slot:activator="{}">
      <slot />
    </template>

    <v-card
      title="Remove source component"
    >
      <template v-slot:append>
        <v-btn
          class="close-btn"
          icon="mdi-close"
          @click="dialog = false"
        />
      </template>

      <v-card-text class="pa-0">
        <v-container
          v-if="sourceComponent"
        >
          Are you sure that you would like to remove
          <b>{{ sourceComponent.name }}</b> source component?
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          text
          class="cancel-btn"
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          color="error"
          text
          class="remove-btn"
          @click="removeSourceComponent"
        >
          Remove
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed } from "vue";

const props = defineProps({
  value: { type: Boolean, default: false },
  sourceComponent: { type: Object, default: () => null }
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

function removeSourceComponent() {
  ccService.getClient().removeSourceComponent(props.sourceComponent.name,
    handleThriftError(success => {
      if (success) {
        emit("on:confirm");
        dialog.value = false;
      }
    }));
}
</script>
