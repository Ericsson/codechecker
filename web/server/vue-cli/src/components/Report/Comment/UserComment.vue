<template>
  <v-timeline-item
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
            class="mr-2"
            tile
          />
          <v-list-item-content>
            <v-list-item-title>
              {{ comment.author }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ comment.createdAt }}
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
import { UserIcon } from "@/components/icons";
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
    comment: { type: Object, required: true },
    bus: { type: Object, required: true }
  },
  computed: {
    message() {
      return this.comment.message.replace(/(?:\r\n|\r|\n)/g, "<br>");
    }
  }
}
</script>