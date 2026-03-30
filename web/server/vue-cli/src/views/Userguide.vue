<template>
  <!-- eslint-disable vue/no-v-text-v-html-on-component -->
  <!-- eslint-disable vue/no-v-html-->
  <v-container fluid v-html="doc" />
</template>

<script setup>
import { onMounted, ref } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

const doc = ref(null);

onMounted(() => {
  import("@/assets/userguide/userguide.md").then(_m => {
    doc.value = DOMPurify.sanitize(marked(_m.default));
  });
});
</script>

<style scoped>
:deep(ul),
:deep(ol) {
  margin-left: 20px;
}

:deep(ul ul),
:deep(ol ol),
:deep(ul ol),
:deep(ol ul) {
  margin-left: 2em;
}
</style>