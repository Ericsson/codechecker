<template>
  <v-dialog
    v-model="dialog"
    content-class="remove-comment-dialog"
    persistent
    max-width="600px"
  >
    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Remove comment

        <v-spacer />

        <v-btn
          icon="mdi-close"
          @click="dialog = false"
        />
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          Are you sure you want to delete this comment?

          <!-- eslint-disable vue/no-v-html -->
          <blockquote
            class="blockquote"
            v-html="message"
          />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          class="cancel-btn"
          color="primary"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          class="remove-btn"
          color="error"
          text
          @click="confirmCommentRemove"
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
  comment: { type: Object, default: () => null }
});

const emit = defineEmits([
  "update:value",
  "on-confirm"
]);

const dialog = computed({
  get: () => props.value,
  set: val => emit("update:value", val)
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