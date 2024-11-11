<template>
  <v-btn
    class="edit-btn"
    icon
    small
    @click="editComment"
  >
    <v-icon
      color="grey lighten-1"
    >
      mdi-pencil
    </v-icon>
  </v-btn>
</template>

<script>
export default {
  name: "EditCommentBtn",
  props: {
    comment: { type: Object, required: true },
    bus: { type: Object, required: true }
  },
  methods: {
    editComment() {
      this.bus.$emit("update:comment", this.comment);
    }
  }
};
</script>
