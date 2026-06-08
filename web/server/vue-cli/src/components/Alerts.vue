<template>
  <span>
    <v-alert
      v-model="success"
      dismissible
      color="success"
      border="left"
      elevation="2"
      colored-border
      icon="mdi-check"
    >
      {{ successMsg }}
    </v-alert>

    <v-alert
      v-model="error"
      dismissible
      color="error"
      border="left"
      elevation="2"
      colored-border
      icon="mdi-alert-outline"
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
  }
};
</script>