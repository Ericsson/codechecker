<template>
  <v-chip
    variant="outlined"
    size="small"
  >
    <v-avatar
      class="mr-0"
      left
    >
      <v-icon
        :color="strToColor(value)"
        size="small"
      >
        mdi-tag-outline
      </v-icon>
    </v-avatar>
    <span
      class="grey--text text--darken-3"
    >
      {{ value }}
    </span>
  </v-chip>
</template>

<script setup>
import { useStrToColor } from "@/composables/useStrToColor";

defineProps({
  value: { type: String, required: true }
});

const { strToColor } = useStrToColor();
</script>
