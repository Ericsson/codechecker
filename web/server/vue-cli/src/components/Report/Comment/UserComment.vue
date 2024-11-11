<template>
  <v-timeline-item
    class="user-comment"
    color="green"
    icon="mdi-account"
    small
    fill-dot
  >
    <v-card
      class="elevation-2"
    >
      <v-list two-line>
        <v-list-item>
          <user-icon
            :value="comment.author"
            :size="32"
            class="mr-2"
            tile
          />
          <v-list-item-content>
            <v-list-item-title>
              {{ comment.author }}
            </v-list-item-title>
            <v-list-item-subtitle
              :title="comment.createdAt"
            >
              {{ createdAt }}
            </v-list-item-subtitle>
          </v-list-item-content>
          <v-list-item-action>
            <div>
              <edit-comment-btn
                :comment="comment"
                :bus="bus"
              />

              <remove-comment-btn
                :comment="comment"
                :bus="bus"
              />
            </div>
          </v-list-item-action>
        </v-list-item>
      </v-list>
      <!-- eslint-disable vue/no-v-html -->
      <v-card-text
        class="pt-0"
        v-html="message"
      />
    </v-card>
  </v-timeline-item>
</template>

<script>
import Vue from "vue";
import { formatDistanceToNow, parse } from "date-fns";

import { CommentData } from "@cc/report-server-types";

import { UserIcon } from "@/components/Icons";
import EditCommentBtn from "./EditCommentBtn";
import RemoveCommentBtn from "./RemoveCommentBtn";

export default {
  name: "UserComment",
  components: {
    EditCommentBtn,
    RemoveCommentBtn,
    UserIcon
  },
  props: {
    comment: { type: CommentData, required: true },
    bus: { type: Vue, required: true }
  },
  computed: {
    message() {
      return this.comment.message.replace(/(?:\r\n|\r|\n)/g, "<br>");
    },
    createdAt() {
      const created = parse(this.comment.createdAt,
        "yyyy-MM-dd HH:mm:ss.SSSSSS", new Date());
      return formatDistanceToNow(created);
    }
  }
};
</script>