<template>
  <v-chip
    v-if="type === 'macro' || type === 'note'"
    :color="color"
    rounded="0"
    size="small"
  >
    <span class="text-weight-bold text-white">{{ index }}</span>
  </v-chip>

  <v-avatar
    v-else
    :color="color"
    size="24"
  >
    <span class="text-caption text-white">{{ index }}</span>
  </v-avatar>
</template>

<script setup>
import { computed } from "vue";
const props = defineProps({
  type: { type: String, default: null },
  index: { type: [ Number, String ], default: null }
});

const color = computed(() => {
  switch (props.type) {
  case "error":
    return "#a94442";
  case "fixit":
    return "#8a6d3b";
  case "macro":
    return "#83876a";
  case "note":
    return "#9299a1";
  default:
    return "#427ea9";
  }
});
</script>
