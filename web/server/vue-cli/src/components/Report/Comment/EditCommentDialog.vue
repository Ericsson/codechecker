<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="edit-comment-dialog"
    persistent
    max-width="600px"
    title="Edit Comment"
    @confirm="confirmCommentChange"
  >
    <template v-slot:content>
      <v-textarea
        v-model="message"
        label="Leave a message..."
        hide-details
        variant="outlined"
      />
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, ref, watch } from "vue";
import ConfirmDialog from "@/components/ConfirmDialog";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  comment: { type: Object, default: () => null }
});

const emit = defineEmits([
  "update:modelValue",
  "on-confirm"
]);

const message = ref(null);

const dialog = computed({
  get: () => props.modelValue,
  set: val => emit("update:modelValue", val)
});

watch(dialog, val => {
  if (val) {
    message.value = props.comment.message;
  }
});

function confirmCommentChange() {
  // TODO: validate the message.
  ccService.getClient().updateComment(props.comment.id, message.value,
    handleThriftError(() => {
      emit("on-confirm");
      dialog.value = false;
    }));
}
</script>