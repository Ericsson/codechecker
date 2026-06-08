<template>
  <v-btn
    class="show-analysis-info-btn"
    title="Show analysis information"
    color="primary"
    size="small"
    icon="mdi-console"
    variant="text"
    @click="$emit('click')"
  >
    Analysis info
  </v-btn>
</template>

<script setup>
defineEmits([ "click" ]);
</script>

