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

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <v-textarea
            v-model="message"
            label="Leave a message..."
            hide-details
            solo
            flat
            outlined
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

<script>
import { ccService, handleThriftError } from "@cc-api";

export default {
  name: "EditCommentDialog",
  props: {
    value: { type: Boolean, default: false },
    comment: { type: Object, default: () => null }
  },
  data() {
    return {
      message: null
    };
  },
  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("update:value", val);
      }
    }
  },
  watch: {
    dialog(val) {
      if (val) {
        this.message = this.comment.message;
      }
    }
  },

  methods: {
    confirmCommentChange() {
      // TODO: validate the message.
      ccService.getClient().updateComment(this.comment.id, this.message,
        handleThriftError(() => {
          this.$emit("on-confirm");
          this.dialog = false;
        }));
    }
  }
};
</script>