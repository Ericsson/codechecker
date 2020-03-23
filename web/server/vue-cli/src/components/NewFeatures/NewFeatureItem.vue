<template>
  <v-card :color="color" :flat="flat">
    <v-card-title class="title">
      <slot name="title" />
    </v-card-title>
    <v-card-text class="white text--primary">
      <v-container>
        <slot />
      </v-container>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: "NewFeatureItem",
  props: {
    color: { type: String, default: null },
    flat: { type: Boolean, default: true }
  }
};
</script>