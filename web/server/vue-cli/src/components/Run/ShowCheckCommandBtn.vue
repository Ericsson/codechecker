<template>
  <v-btn
    class="show-check-command"
    title="Show check command"
    color="grey darken-1"
    small
    text
    icon
    @click="$emit('click')"
  >
    <v-icon>mdi-console</v-icon>
  </v-btn>
</template>

<script>
export default {
  name: "ShowCheckCommandBtn",
};
</script>
