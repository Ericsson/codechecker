<template>
  <v-tooltip
    max-width="300"
    color="black"
    right
  >
    <template v-slot:activator="{ on }">
      <slot :on="on" name="activator">
        <v-icon
          :color="color"
          class="ml-1"
          small
          v-on="on"
        >
          mdi-help-circle
        </v-icon>
      </slot>
    </template>
    <slot />
  </v-tooltip>
</template>

<script>
export default {
  name: "TooltipHelpIcon",
  props: {
    color: { type: String, default: "accent" }
  }
};
</script>
