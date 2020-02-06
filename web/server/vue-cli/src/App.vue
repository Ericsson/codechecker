<template>
  <v-app id="app">
    <the-header />

    <v-content>
      <v-container
        class="py-0 pb-2"
        fluid
      >
        <v-row>
          <v-col class="py-0">
            <router-view />
          </v-col>
        </v-row>
      </v-container>
    </v-content>

    <the-footer />
  </v-app>
</template>

<script>
import TheFooter from "@/components/TheFooter"
import TheHeader from "@/components/TheHeader"

export default {
  name: "App",
  components: {
    TheFooter,
    TheHeader
  }
}
</script>

<style lang="scss">
html {
  overflow-y: auto;
}
</style>