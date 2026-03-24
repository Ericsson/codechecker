<template>
  <v-container
    class="pa-0"
    :style="{'position': 'relative'}"
  >
    <v-overlay :absolute="true" :opacity="0.25" :value="loading">
      <v-progress-circular indeterminate size="64" />
    </v-overlay>

    <edit-comment-dialog
      v-model="editDialog"
      :comment="selected"
      @on-confirm="fetchComments"
    />

    <remove-comment-dialog
      v-model="removeDialog"
      :comment="selected"
      @on-confirm="fetchComments"
    />

    <new-comment
      :comments="comments"
      :report="report"
      :bus="bus"
      @new:comments="onNewComment"
    />

    <v-container
      fluid
      class="px-0"
    >
      <v-row
        class="ma-0"
      >
        <v-col
          cols="auto"
        >
          <v-timeline
            v-if="comments.length"
            density="compact"
            color="primary"
          >
            <template
              v-for="comment in comments"
            >
              <user-comment
                v-if="comment.kind === CommentKind.USER"
                :key="comment.id.toString()"
                :comment="comment"
                @update:comment="openEditCommentDialog"
                @remove:comment="openRemoveCommentDialog"
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
  </v-container>
</template>

<script setup>
import mitt from "mitt";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

import { ccService, handleThriftError } from "@cc-api";
import { CommentKind } from "@cc/report-server-types";

import EditCommentDialog from "./EditCommentDialog";
import NewComment from "./NewComment";
import RemoveCommentDialog from "./RemoveCommentDialog";
import SystemComment from "./SystemComment";
import UserComment from "./UserComment";

const props = defineProps({
  report: { type: Object, default: () => null }
});

const emit = defineEmits([ "update:commentCount" ]);

const comments = ref([]);
const selected = ref(null);
const editDialog = ref(false);
const removeDialog = ref(false);
const loading = ref(false);
const bus = mitt();

function fetchComments() {
  if (!props.report) return;

  loading.value = true;
  ccService.getClient().getComments(props.report.reportId,
    handleThriftError(_comments => {
      comments.value = _comments;
      loading.value = false;
    }));
}

function onNewComment() {
  emit("update:commentCount", props.report);
  fetchComments();
}

function openEditCommentDialog(comment) {
  selected.value = comment;
  editDialog.value = true;
}

function openRemoveCommentDialog(comment) {
  selected.value = comment;
  removeDialog.value = true;
}

watch(() => props.report, () => {
  fetchComments();
});

onMounted(() => {
  fetchComments();
});

onBeforeUnmount(() => {
  bus.off("update:comments", fetchComments);
  bus.off("update:comment");
  bus.off("remove:comment");
});
</script>

<style lang="scss">
:deep(.v-timeline-item .v-timeline-item__dot) {
  background-color: var(--v-theme-primary) !important;
}

:deep(.v-timeline-item .v-timeline-item__dot .v-icon) {
  color: white !important;
}
</style>
