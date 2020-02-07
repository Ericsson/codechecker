<template>
  <v-container>
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
      bus: new Vue()
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
