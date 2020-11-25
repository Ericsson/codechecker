<template>
  <v-tooltip
    max-width="300"
    color="black"
    right
  >
    <template v-slot:activator="{ on }">
      <v-icon
        color="accent"
        class="ml-1"
        small
        v-on="on"
      >
        mdi-help-circle
      </v-icon>
    </template>
    <slot />
  </v-tooltip>
</template>

<script>
export default {
  name: "TooltipHelpIcon"
};
</script>
