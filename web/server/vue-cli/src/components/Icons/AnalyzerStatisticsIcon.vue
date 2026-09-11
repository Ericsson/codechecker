<template>
  <v-icon
    v-if="value === 'successful'"
    class="analyzer-statistics-icon-successful"
    color="var(--color-soft-green)"
  >
    mdi-check
  </v-icon>

  <v-icon
    v-else-if="value === 'failed'"
    class="analyzer-statistics-icon-failed"
    color="var(--color-soft-red)"
  >
    mdi-close
  </v-icon>
</template>

<script setup>
defineProps({
  value: { type: String, required: true }
});
</script>
