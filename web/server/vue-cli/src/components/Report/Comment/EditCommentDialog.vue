<template>
  <v-dialog
    v-model="dialog"
    content-class="edit-comment-dialog"
    persistent
    max-width="600px"
  >
    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Edit comment

        <v-spacer />

        <v-btn
          icon="mdi-close"
          @click="dialog = false"
        />
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <v-textarea
            v-model="message"
            label="Leave a message..."
            hide-details
            variant="outlined"
          />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          class="cancel-btn"
          color="error"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          class="save-btn"
          color="primary"
          text
          @click="confirmCommentChange"
        >
          Change
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, ref, watch } from "vue";

const props = defineProps({
  value: { type: Boolean, default: false },
  comment: { type: Object, default: () => null }
});

const emit = defineEmits([
  "update:value",
  "on-confirm"
]);

const message = ref(null);

const dialog = computed({
  get: () => props.value,
  set: val => emit("update:value", val)
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