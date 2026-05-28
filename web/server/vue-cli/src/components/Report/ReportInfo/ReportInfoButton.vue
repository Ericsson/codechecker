<template>
  <v-btn
    v-bind="props"
    color="primary"
    class="show-report-info-btn"
    variant="outlined"
    prepend-icon="mdi-help-circle-outline"
    size="small"
  >
    Report info
  </v-btn>
</template>

<script setup>
defineProps({
  props: { type: Object, default: null }
});
</script>
