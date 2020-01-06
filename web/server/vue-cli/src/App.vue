<template>
  <v-app id="app">
    <router-link :to="{ name: 'products' }">
      Products
    </router-link>
    <router-link :to="{ name: 'login' }">
      Login
    </router-link>
    <router-link :to="{ name: 'global-permission' }">
      Global permissions
    </router-link>
    <router-link :to="{ name: 'product-new' }">
      New product
    </router-link>
    <router-link :to="{ name: 'product-edit', params: { endpoint: 'Default' } }">
      Edit product
    </router-link>
    <router-link :to="{ name: 'product-permission', params: { endpoint: 'Default' } }">
      Product permissions
    </router-link>
    <router-link :to="{ name: 'runs', params: { endpoint: 'Default' } }">
      Product detail
    </router-link>
    <v-btn class="ma-2" tile outlined color="success">
      <v-icon left>
        mdi-pencil
      </v-icon> Edit
    </v-btn>
    <router-view />
  </v-app>
</template>

<script>
import { VApp } from "Vuetify/VApp";
import { VBtn } from "Vuetify/VBtn";
import { VIcon } from "Vuetify/VIcon";

export default {
  name: 'App',
  components: {
    VApp, VBtn, VIcon
  }
}
</script>
