<template>
  <v-card
    :flat="false"
  >
    <v-card-title
      :class="[`${color}`]"
    >
      <slot name="title" />
    </v-card-title>

    <v-card-text>
      <slot />
    </v-card-text>
  </v-card>
</template>

<script setup>
defineProps({
  color: { type: String, default: "primary" }
});
</script>