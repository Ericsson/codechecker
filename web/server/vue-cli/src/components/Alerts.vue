<template>
  <span>
    <v-alert
      v-if="success"
      dismissible
      color="success"
      border="start"
      elevation="2"
      colored-border
      icon="mdi-check"
    >
      {{ successMsg }}
    </v-alert>

    <v-alert
      v-if="error"
      dismissible
      color="error"
      border="start"
      elevation="2"
      colored-border
      icon="mdi-alert-outline"
    >
      {{ errorMsg }}
    </v-alert>
  </span>
</template>

<script setup>
defineProps({
  success: { type: Boolean, default: false },
  error: { type: Boolean, default: false },
  successMsg: { type: String, default: null },
  errorMsg: { type: String, default: null },
});
</script>