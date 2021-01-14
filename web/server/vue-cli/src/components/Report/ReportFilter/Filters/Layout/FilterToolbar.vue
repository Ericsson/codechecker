<template>
  <v-expansion-panels
    v-model="value"
    flat
  >
    <v-expansion-panel>
      <v-expansion-panel-header class="pa-0" hide-actions>
        <v-toolbar flat dense>
          <v-toolbar-title class="font-weight-bold body-2">
            <v-icon class="expansion-btn">
              {{ value == 0 ? "mdi-chevron-up" : "mdi-chevron-down" }}
            </v-icon>
            {{ title }}

            <slot name="append-toolbar-title" />
          </v-toolbar-title>

          <slot name="prepend-toolbar-title" />

          <v-spacer />

          <v-toolbar-items>
            <slot name="prepend-toolbar-items" />

            <v-btn
              icon
              small
              class="clear-btn"
              @click.stop="clear"
            >
              <v-icon>mdi-delete</v-icon>
            </v-btn>

            <slot name="append-toolbar-items" />
          </v-toolbar-items>
        </v-toolbar>
      </v-expansion-panel-header>

      <v-expansion-panel-content>
        <slot />
      </v-expansion-panel-content>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script>
export default {
  name: "FilterToolbar",
  props: {
    title: { type: String, required: true },
    panel: { type: Boolean, default: false }
  },

  data() {
    return {
      value: this.panel ? 0 : null
    };
  },

  watch: {
    panel() {
      this.value = this.panel ? 0 : null;
    }
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

::v-deep .selected-items {
  color: grey;
}
</style>