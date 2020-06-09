<template>
  <v-container class="py-0">
    <v-row>
      <v-textarea
        v-model="message"
        outlined
        name="message"
        label="Leave a message..."
        hide-details
      />
    </v-row>

    <v-row>
      <v-spacer />
      <v-col
        cols="auto"
        class="px-0"
      >
        <v-btn
          class="new-comment-btn"
          color="primary"
          small
          :loading="loading"
          @click="addNewComment"
        >
          <v-icon small>
            mdi-plus
          </v-icon>
          Add
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { CommentData } from "@cc/report-server-types";

export default {
  name: "NewComment",
  props: {
    comments: { type: Array, required: true },
    report: { type: Object, default: () => null },
    bus: { type: Object, required: true }
  },
  data() {
    return {
      message: null,
      loading: false
    };
  },
  methods: {
    addNewComment() {
      if (!this.message) return;

      this.loading = true;
      const commentData = new CommentData({ message: this.message });
      ccService.getClient().addComment(this.report.reportId, commentData,
        handleThriftError(() => {
          this.bus.$emit("update:comments");
          this.message = null;
          this.loading = false;
        }));
    }
  }
};
</script>
