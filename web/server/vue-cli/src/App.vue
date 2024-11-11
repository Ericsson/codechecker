<template>
  <v-app id="app">
    <the-header />

    <v-main>
      <keep-alive :include="keepAliveList">
        <router-view />
      </keep-alive>
      <errors />
    </v-main>
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
  },
  data() {
    return {
      keepAliveList: []
    };
  },
  computed: {
    isAuthenticated() {
      return this.$store.getters.isAuthenticated;
    }
  },
  watch: {
    // eslint-disable-next-line no-unused-vars
    isAuthenticated(newValue, _) {
      if (newValue) {
        this.keepAliveList.push("Products");
      } else {
        this.keepAliveList = [];
      }
    },
  },
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
