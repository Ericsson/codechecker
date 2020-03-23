<template>
  <v-app id="app">
    <the-header />

    <v-content>
      <router-view />

      <errors />
    </v-content>
  </v-app>
</template>

<script>
import Errors from "@/components/Errors";
import { TheHeader } from "@/components/Layout";

export default {
  name: "App",
  components: {
    Errors,
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