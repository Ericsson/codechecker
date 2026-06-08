<template>
  <v-timeline-item
    class="system-comment"
    dot-color="primary"
    icon="mdi-cogs"
    size="small"
    fill-dot
  >
    <v-card
      class="elevation-2"
    >
      <v-card-text
        class="caption"
      >
        <template v-for="(part, index) in messageParts" :key="index">
          <strong v-if="part.bold">{{ part.text }}</strong>
          <!-- eslint-disable vue/no-v-html -->
          <span v-else v-html="part.text" />
        </template>
      </v-card-text>
    </v-card>
  </v-timeline-item>
</template>

<script setup>
import { computed } from "vue";
import DOMPurify from "dompurify";

const props = defineProps({
  comment: { type: Object, required: true },
});

const messageParts = computed(() => {
  const msg = props.comment.message;
  const parts = [];
  const authorIndex = msg.indexOf("%author%");
  const dateIndex = msg.indexOf("%date%");
  
  if (authorIndex === -1 && dateIndex === -1) {
    return [ { text: msg, bold: false } ];
  }
  
  let currentIndex = 0;
  
  // Handle author replacement
  if (authorIndex !== -1) {
    if (authorIndex > currentIndex) {
      parts.push({ text: msg.slice(currentIndex, authorIndex), bold: false });
    }
    parts.push({ text: props.comment.author, bold: true });
    currentIndex = authorIndex + "%author%".length;
  }
  
  // Handle date replacement
  if (dateIndex !== -1 && dateIndex >= currentIndex) {
    if (dateIndex > currentIndex) {
      parts.push({ text: msg.slice(currentIndex, dateIndex), bold: false });
    }
    parts.push({ text: props.comment.createdAt, bold: false });
    currentIndex = dateIndex + "%date%".length;
  }
  
  // Add remaining text
  if (currentIndex < msg.length) {
    const dirtyMessage = msg.slice(currentIndex);
    parts.push(
      { text: DOMPurify.sanitize(dirtyMessage), bold: false }
    );
  }
  
  return parts;
});
</script>
