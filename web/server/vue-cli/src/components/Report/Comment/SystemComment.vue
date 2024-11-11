<template>
  <v-timeline-item
    class="system-comment"
    color="primary"
    icon="mdi-cogs"
    small
    fill-dot
  >
    <v-card class="elevation-2">
      <!-- eslint-disable vue/no-v-html -->
      <v-card-text
        class="caption"
        v-html="message"
      />
    </v-card>
  </v-timeline-item>
</template>

<script>
export default {
  name: "SystemComment",
  props: {
    comment: { type: Object, required: true },
  },
  computed: {
    message() {
      return this.comment.message
        .replace("%author%", `<b>${ this.comment.author }</b>`)
        .replace("%date%", this.comment.createdAt);
    }
  }
};
</script>
