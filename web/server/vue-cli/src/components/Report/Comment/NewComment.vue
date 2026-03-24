<template>
  <v-container class="py-0">
    <v-row class="ma-0">
      <v-textarea
        v-model="message"
        variant="outlined"
        name="message"
        label="Leave a message..."
        hide-details
      />
    </v-row>

    <v-row class="ma-0">
      <v-spacer />
      <v-col
        cols="auto"
        class="px-0"
      >
        <v-btn
          class="new-comment-btn"
          color="primary"
          size="small"
          :loading="loading"
          @click="addNewComment"
        >
          <v-icon
            size="small"
          >
            mdi-plus
          </v-icon>
          Add
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { CommentData } from "@cc/report-server-types";
import { ref } from "vue";

const props = defineProps({
  comments: { type: Array, required: true },
  report: { type: Object, default: () => null }
});

const emit = defineEmits([ "new:comments" ]);

const message = ref(null);
const loading = ref(false);

function addNewComment() {
  if (!message.value) return;

  loading.value = true;
  const _commentData = new CommentData({ message: message.value });
  ccService.getClient().addComment(props.report.reportId, _commentData,
    handleThriftError(() => {
      emit("new:comments");
      message.value = null;
      loading.value = false;
    }));
}
</script>
