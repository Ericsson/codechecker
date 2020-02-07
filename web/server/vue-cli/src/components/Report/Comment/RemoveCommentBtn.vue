<template>
  <v-btn
    icon
    @click="removeComment"
  >
    <v-icon color="grey lighten-1">
      mdi-trash-can-outline
    </v-icon>
  </v-btn>
</template>

<script>
import { ccService } from "@cc-api";

export default {
  name: "RemoveCommentBtn",
  props: {
    comment: { type: Object, required: true },
    bus: { type: Object, required: true }
  },
  methods: {
    removeComment() {
      // TODO: confirmation dialog before remove.
      ccService.getClient().removeComment(this.comment.id, (/* err */) => {
        this.bus.$emit("remove:comment", this.comment.id);
      });
    }
  }
}
</script>
