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
      </v-list>
    </v-menu>
  </v-app-bar>
</template>

<script>
export default {
  name: "TheHeader"
};
</script>
