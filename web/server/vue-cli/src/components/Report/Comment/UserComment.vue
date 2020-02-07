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
      <v-card-title>
        {{ comment.author }}
        <v-spacer />

        <edit-comment-btn />

        <remove-comment-btn
          :comment="comment"
          :bus="bus"
        />
      </v-card-title>
      <v-card-subtitle>
        {{ comment.createdAt }}
      </v-card-subtitle>
      <v-card-text>
        {{ comment.message }}
      </v-card-text>
    </v-card>
  </v-timeline-item>
</template>

<script>
import EditCommentBtn from "./EditCommentBtn";
import RemoveCommentBtn from "./RemoveCommentBtn";

export default {
  name: "UserComment",
  components: {
    EditCommentBtn,
    RemoveCommentBtn
  },
  props: {
    comment: { type: Object, required: true },
    bus: { type: Object, required: true }
  }
}
</script>