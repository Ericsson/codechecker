<template>
  <v-menu
    content-class="run-description-menu"
    :close-on-content-click="false"
    :nudge-width="200"
    offset-x
  >
    <template v-slot:activator="{ props }">
      <v-icon
        v-bind="props"
        color="primary"
        class="description"
      >
        mdi-information-outline
      </v-icon>
    </template>
    <v-card>
      <v-card-title>Description</v-card-title>
      <v-card-text>{{ value }}</v-card-text>
    </v-card>
  </v-menu>
</template>

<script setup>
defineProps({
  value: { type: String, required: true }
});
</script>
