<template>
  <v-container
    class="py-1"
    :style="{'position': 'relative'}"
  >
    <v-overlay :absolute="true" :opacity="0.25" :value="loading">
      <v-progress-circular indeterminate size="64" />
    </v-overlay>

    <edit-comment-dialog
      :value.sync="editDialog"
      :comment="selected"
      @on-confirm="fetchComments"
    />

    <remove-comment-dialog
      :value.sync="removeDialog"
      :comment="selected"
      @on-confirm="fetchComments"
    />

    <new-comment
      :comments="comments"
      :report="report"
      :bus="bus"
    />

    <v-row>
      <v-col cols="auto">
        <v-timeline
          v-if="comments.length"
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
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import Vue from "vue";

import { ccService, handleThriftError } from "@cc-api";
import { CommentKind } from "@cc/report-server-types";

import EditCommentDialog from "./EditCommentDialog";
import NewComment from "./NewComment";
import UserComment from "./UserComment";
import RemoveCommentDialog from "./RemoveCommentDialog";
import SystemComment from "./SystemComment";

export default {
  name: "ReportComments",
  components: {
    EditCommentDialog,
    NewComment,
    UserComment,
    RemoveCommentDialog,
    SystemComment
  },
  props: {
    report: { type: Object, default: () => null }
  },

  data() {
    return {
      CommentKind,
      comments: [],
      selected: null,
      editDialog: false,
      removeDialog: false,
      loading: false,
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

    this.bus.$on("update:comment", comment => {
      this.selected = comment;
      this.editDialog = true;
    });

    this.bus.$on("remove:comment", comment => {
      this.selected = comment;
      this.removeDialog = true;
    });
  },

  methods: {
    fetchComments() {
      if (!this.report) return;

      this.loading = true;
      ccService.getClient().getComments(this.report.reportId,
        handleThriftError(comments => {
          this.comments = comments;
          this.loading = false;
        }));
    }
  }
};
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
