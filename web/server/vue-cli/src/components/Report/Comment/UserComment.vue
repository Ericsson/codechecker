<template>
  <v-timeline-item
    class="user-comment"
    dot-color="green"
    icon="mdi-account"
    size="small"
    fill-dot
  >
    <v-card
      class="elevation-2"
    >
      <v-list
        lines="two"
      >
        <v-list-item>
          <template v-slot:prepend>
            <user-icon
              :value="comment.author"
              :size="32"
              class="mr-2"
              rounded="0"
            />
          </template>

          <v-list-item-title>
            {{ comment.author }}
          </v-list-item-title>

          <v-list-item-subtitle
            :title="comment.createdAt"
          >
            {{ createdAt }}
          </v-list-item-subtitle>
          <template v-slot:append>
            <div>
              <edit-comment-btn
                class="mr-2"
                :comment="comment"
                @update:comment="updateComment"
              />

              <remove-comment-btn
                :comment="comment"
                @remove:comment="removeComment"
              />
            </div>
          </template>
        </v-list-item>
      </v-list>
      <v-card-text class="pt-0 preserve-whitespace">
        {{ comment.message }}
      </v-card-text>
    </v-card>
  </v-timeline-item>
</template>

<script setup>
import { formatDistanceToNow, parse } from "date-fns";
import { computed } from "vue";

import { UserIcon } from "@/components/Icons";
import EditCommentBtn from "./EditCommentBtn";
import RemoveCommentBtn from "./RemoveCommentBtn";

const props = defineProps({
  comment: { type: Object, required: true },
  bus: { type: Object, required: true }
});

const createdAt = computed(() => {
  const created = parse(props.comment.createdAt,
    "yyyy-MM-dd HH:mm:ss.SSSSSS", new Date());
  return formatDistanceToNow(created);
});

function updateComment(comment) {
  props.bus.emit("update:comment", comment);
}

function removeComment(comment) {
  props.bus.emit("remove:comment", comment);
}
</script>

<style scoped>
.preserve-whitespace {
  white-space: pre-wrap;
}
</style>