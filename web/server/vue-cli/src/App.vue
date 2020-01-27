<template>
  <v-app id="app">
    <the-header />

    <v-content>
      <v-container fluid>
        <v-row>
          <v-col>
            <router-view />
          </v-col>
        </v-row>
      </v-container>
    </v-content>

    <the-footer />
  </v-app>
</template>

<script>
import { VApp } from "Vuetify/VApp";
import VContainer from "Vuetify/VGrid/VContainer";
import { VContent } from "Vuetify/VContent";
import VRow from "Vuetify/VGrid/VRow";
import VCol from "Vuetify/VGrid/VCol";

import TheFooter from "@/components/TheFooter"
import TheHeader from "@/components/TheHeader"

export default {
  name: "App",
  components: {
    TheFooter,
    TheHeader,
    VApp, VContainer, VContent, VRow, VCol
  }
}
</script>

<style lang="scss">
html {
  overflow-y: hidden;
}
</style>