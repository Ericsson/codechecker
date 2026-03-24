<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="remove-comment-dialog"
    persistent
    max-width="600px"
    title="Remove Comment"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    @confirm="confirmCommentRemove"
  >
    <template v-slot:content>
      <v-container>
        Are you sure you want to delete this comment?

        <!-- eslint-disable vue/no-v-html -->
        <blockquote
          class="blockquote"
          v-html="message"
        />
      </v-container>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed } from "vue";
import ConfirmDialog from "@/components/ConfirmDialog";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  comment: { type: Object, default: () => null }
});

const emit = defineEmits([
  "update:modelValue",
  "on-confirm"
]);

const dialog = computed({
  get: () => props.modelValue,
  set: val => emit("update:modelValue", val)
});

const message = computed(() => props.comment ? props.comment.message : null);

function confirmCommentRemove() {
  ccService.getClient().removeComment(props.comment.id,
    handleThriftError(() => {
      emit("on-confirm");
      dialog.value = false;
    }));
}
</script>