<template>
  <v-card
    :flat="flat"
  >
    <v-card-title
      :class="[`${color}`]"
    >
      <slot name="title" />
    </v-card-title>
    <v-card-text
      class="bg-white text-black"
    >
      <v-container>
        <slot />
      </v-container>
    </v-card-text>
  </v-card>
</template>

<script setup>
defineProps({
  color: { type: String, default: null },
  flat: { type: Boolean, default: true }
});
</script>