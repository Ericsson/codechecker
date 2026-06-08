<template>
  <v-tooltip
    max-width="300"
    color="black"
    location="right"
    content-class="pa-6"
  >
    <template v-slot:activator="{ props }">
      <slot
        v-bind="props"
        name="activator"
      >
        <v-icon
          v-bind="props"
          :color="color"
          :size="size"
        >
          mdi-help-circle
        </v-icon>
      </slot>
    </template>
    <slot />
  </v-tooltip>
</template>

<script setup>
defineProps({
  color: { type: String, default: "accent" },
  size: { type: String, default: "small" }
});
</script>
