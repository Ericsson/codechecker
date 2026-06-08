<template>
  <v-dialog
    v-model="dialog"
    persistent
    :content-class="contentClass"
    :max-width="maxWidth"
    :scrollable="scrollable"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <slot name="activator" :props="activatorProps" />
    </template>

    <v-card
      v-if="loading"
      color="bg-primary"
    >
      <v-card-text>
        Loading...
        <v-progress-linear
          indeterminate
          color="white"
          class="mb-0"
        />
      </v-card-text>
    </v-card>

    <v-card
      v-else
      :title="props.title"
    >
      <template v-slot:append>
        <v-btn
          class="close-btn"
          icon="mdi-close"
          size="small"
          @click="dialog = false"
        />
      </template>

      <v-progress-linear v-if="confirmInProgress" indeterminate />

      <v-card-text class="pa-0">
        <v-container fluid>
          <slot name="content" />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions
        v-if="props.buttons"
      >
        <v-spacer />

        <v-btn
          variant="text"
          class="cancel-btn"
          :color="cancelBtnColor"
          @click="cancelDialog()"
        >
          {{ cancelBtnLabel }}
        </v-btn>

        <v-btn
          variant="text"
          class="confirm-btn"
          :color="confirmBtnColor"
          @click="emit('confirm')"
        >
          {{ confirmBtnLabel }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  buttons: { type: Boolean, default: true },
  cancelBtnLabel: { type: String, default: "Cancel" },
  cancelBtnColor: { type: String, default: "grey" },
  confirmBtnLabel: { type: String, default: "Save" },
  confirmBtnColor: { type: String, default: "primary" },
  confirmInProgress: { type: Boolean, default: false },
  maxWidth: { type: String, default: "600px" },
  scrollable: { type: Boolean, default: true },
  loading: { type: Boolean, default: false },
  contentClass: { type: String, default: null },
  title: { type: String, default: null }
});

const emit = defineEmits([
  "confirm",
  "cancel",
  "update:modelValue"
]);

const dialog = computed({
  get() {
    return props.modelValue;
  },
  set(value) {
    emit("update:modelValue", value);
  }
});

function cancelDialog() {
  emit("cancel");
  dialog.value = false;
}
</script>
