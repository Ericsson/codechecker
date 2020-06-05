<template>
  <v-card flat>
    <v-toolbar flat dense>
      <v-toolbar-title class="font-weight-bold body-2">
        {{ title }}
      </v-toolbar-title>

      <slot name="prepend-toolbar-title" />

      <v-spacer />

      <v-toolbar-items>
        <slot name="prepend-toolbar-items" />

        <v-btn
          icon
          small
          class="clear-btn"
          @click="clear(true)"
        >
          <v-icon>mdi-delete</v-icon>
        </v-btn>

        <slot name="append-toolbar-items" />
      </v-toolbar-items>
    </v-toolbar>

    <slot />
  </v-card>
</template>

<script>
export default {
  name: "FilterToolbar",
  props: {
    title: { type: String, required: true }
  },

  methods: {
    clear() {
      this.$emit("clear");
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .v-toolbar > .v-toolbar__content {
  padding: 0;
}
</style>