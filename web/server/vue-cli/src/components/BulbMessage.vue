<template>
  <v-container class="pa-4 pb-0 caption">
    <v-icon class="mr-1" :color="color">
      mdi-lightbulb-on-outline
    </v-icon>

    <slot />
  </v-container>
</template>

<script>
export default {
  name: "BulbMessage",
  props: {
    color: { type: String, default: "orange" }
  }
};
</script>
