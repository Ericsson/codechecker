<template>
  <new-feature-item :color="color" :flat="false">
    <template v-slot:title>
      <slot name="title" />
    </template>

    <template v-slot>
      <slot />
    </template>
  </new-feature-item>
</template>

<script>
import NewFeatureItem from "./NewFeatureItem";

export default {
  name: "NewReleaseItem",
  components: {
    NewFeatureItem
  },
  props: {
    color: { type: String, default: "primary" }
  }
};
</script>