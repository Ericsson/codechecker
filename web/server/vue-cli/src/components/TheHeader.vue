<template>
  <v-app-bar app color="primary" dark>
    <v-toolbar-title>CodeChecker</v-toolbar-title>

    <v-spacer />

    <v-menu offset-y>
      <template v-slot:activator="{ on }">
        <v-btn color="secondary" v-on="on">
          Menu
        </v-btn>
      </template>
      <v-list>
        <v-list-item :to="{ name: 'products' }">
          <v-list-item-title>Products</v-list-item-title>
        </v-list-item>
        <v-list-item :to="{ name: 'login' }">
          <v-list-item-title>Login</v-list-item-title>
        </v-list-item>
        <v-list-item :to="{ name: 'runs', params: { endpoint: 'Default' } }">
          <v-list-item-title>Product detail</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
  </v-app-bar>
</template>

<script>
import { VAppBar } from "Vuetify/VAppBar";
import { VBtn } from "Vuetify/VBtn";
import { VList, VListItem, VListItemTitle } from "Vuetify/VList";
import { VMenu } from "Vuetify/VMenu";
import VSpacer from "Vuetify/VGrid/VSpacer";
import { VToolbarTitle } from "Vuetify/VToolbar";

export default {
  name: "TheHeader",
  components: {
    VAppBar, VBtn, VList, VListItem, VListItemTitle, VMenu, VSpacer,
    VToolbarTitle
  }
};
</script>
