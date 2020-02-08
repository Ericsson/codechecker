<template>
  <v-container>
    <v-dialog
      v-model="dialog"
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
            color="error"
            text
            @click="dialog = false"
          >
            Cancel
          </v-btn>

          <v-btn
            color="primary"
            text
            @click="confirmCommentChange"
          >
            Change
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <new-comment
      :comments="comments"
      :report="report"
      :bus="bus"
    />

    <v-row>
      <v-timeline
        dense
      >
        <template
          v-for="comment in comments"
        >
          <user-comment
            v-if="comment.kind === CommentKind.USER"
            :key="comment.id.toString()"
            :comment="comment"
            :bus="bus"
          />

          <system-comment
            v-if="comment.kind === CommentKind.SYSTEM"
            :key="comment.id.toString()"
            :comment="comment"
          />
        </template>
      </v-timeline>
    </v-row>
  </v-container>
</template>

<script>
import Vue from "vue";

import { ccService } from "@cc-api";
import { CommentKind } from "@cc/report-server-types";

import NewComment from "./NewComment";
import UserComment from "./UserComment";
import SystemComment from "./SystemComment";

export default {
  name: "ReportComments",
  components: {
    NewComment,
    UserComment,
    SystemComment
  },
  props: {
    report: { type: Object, default: () => null }
  },

  data() {
    return {
      CommentKind,
      comments: [],
      bus: new Vue(),
      comment: null,
      message: null,
      dialog: false
    };
  },

  watch: {
    report() {
      this.fetchComments();
    }
  },

  mounted() {
    this.fetchComments();

    this.bus.$on("update:comments", this.fetchComments);

    this.bus.$on("update:comment", (comment) => {
      this.comment = comment;
      this.message = comment.message;
      this.dialog = true;
    });

    this.bus.$on("remove:comment", (commentId) => {
      this.comments = this.comments.filter((comment) => {
        return comment.id !== commentId;
      });
    });
  },

  methods: {
    fetchComments() {
      if (!this.report) return;

      ccService.getClient().getComments(this.report.reportId,
      (err, comments) => {
        this.comments = comments;
      });
    },
    confirmCommentChange() {
      // TODO: validate the message.
      ccService.getClient().updateComment(this.comment.id, this.message,
      () => {
        this.fetchComments();
        this.dialog = false;
      });
    }
  }
}
</script>

<style lang="scss" scoped>
$width: 48px;

::v-deep .v-timeline-item__divider {
  min-width: $width;
}

.v-timeline--dense ::v-deep .v-timeline-item__body {
  max-width: calc(100% - #{$width});
}

.v-application--is-ltr .v-timeline--dense:not(.v-timeline--reverse):before {
  left: calc((#{$width} / 2) - 1px)
}
</style>
