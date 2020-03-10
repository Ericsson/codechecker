<template>
  <v-app id="app">
    <the-header />

    <v-content>
      <router-view />
    </v-content>

    <the-footer />
  </v-app>
</template>

<script>
import { TheFooter, TheHeader } from "@/components/Layout";

export default {
  name: "App",
  components: {
    TheFooter,
    TheHeader
  }
};
</script>

<style lang="scss">
html {
  overflow-y: auto;
}

.v-text-field.v-text-field--solo.small {
  & > .v-input__control {
    min-height: 30px;

    & > .v-input__slot {
      min-height: 30px;

      .v-select__selections {
        font-size: 0.75rem;
      }
    }
  }
}
</style>