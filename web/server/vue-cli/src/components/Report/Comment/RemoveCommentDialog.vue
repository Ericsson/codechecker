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

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
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

<script>
import { ccService, handleThriftError } from "@cc-api";

export default {
  name: "RemoveCommentDialog",
  props: {
    value: { type: Boolean, default: false },
    comment: { type: Object, default: () => null }
  },
  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("update:value", val);
      }
    },
    message() {
      return this.comment ? this.comment.message : null;
    }
  },

  methods: {
    confirmCommentRemove() {
      ccService.getClient().removeComment(this.comment.id,
        handleThriftError(() => {
          this.$emit("on-confirm");
          this.dialog = false;
        }));
    }
  }
};
</script>