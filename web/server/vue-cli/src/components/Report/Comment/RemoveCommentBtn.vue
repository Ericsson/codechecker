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
export default {
  name: "RemoveCommentBtn",
  props: {
    comment: { type: Object, required: true },
    bus: { type: Object, required: true }
  },
  methods: {
    removeComment() {
      this.bus.$emit("remove:comment", this.comment);
    }
  }
}
</script>
