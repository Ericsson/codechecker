<template>
  <v-chip
    variant="outlined"
  >
    <v-icon
      :color="strToColor(value)"
      start
    >
      mdi-tag-outline
    </v-icon>
    {{ value }}
  </v-chip>
</template>

<script setup>
import { useStrToColor } from "@/composables/useStrToColor";

defineProps({
  value: { type: String, required: true }
});

const { strToColor } = useStrToColor();
</script>
