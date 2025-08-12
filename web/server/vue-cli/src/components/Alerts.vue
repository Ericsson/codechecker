<template>
  <span>
    <v-alert
      :model-value="success"
      dismissible
      color="success"
      border="left"
      elevation="2"
      colored-border
      icon="mdi-check"
      @update:model-value="$emit('update:success', $event)"
    >
      {{ successMsg }}
    </v-alert>

    <v-alert
      :model-value="error"
      dismissible
      color="error"
      border="left"
      elevation="2"
      colored-border
      icon="mdi-alert-outline"
      @update:model-value="$emit('update:error', $event)"
    >
      {{ errorMsg }}
    </v-alert>
  </span>
</template>

<script>
export default {
  name: "Alerts",
  props: {
    success: { type: Boolean, default: false },
    error: { type: Boolean, default: false },
    successMsg: { type: String, default: null },
    errorMsg: { type: String, default: null }
  },
  emits: [
    "update:success",
    "update:error"
  ]
};
</script>
