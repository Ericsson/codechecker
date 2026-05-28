<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="remove-source-component-dialog"
    title="Remove source component"
    confirm-btn-color="error"
    confirm-btn-label="Remove"
    @confirm="removeSourceComponent"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        class="remove-btn"
        icon="mdi-trash-can-outline"
        color="error"
        variant="tonal"
        size="small"
      />
    </template>
    <template v-slot:content>
      <p>
        Are you sure that you would like to remove
        <b>{{ sourceComponent.name }}</b> source component?
      </p>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import ConfirmDialog from "@/components/ConfirmDialog";
import { ref } from "vue";

const props = defineProps({
  sourceComponent: { type: Object, default: () => null }
});

const emit = defineEmits([ "on:confirm" ]);

const dialog = ref(false);

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
