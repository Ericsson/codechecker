<template>
  <v-app-bar app color="primary" dark>
    <v-app-bar-nav-icon>
      <v-avatar
        size="36px"
      >
        <img
          alt="Logo"
          src="@/assets/logo.png"
        >
      </v-avatar>
    </v-app-bar-nav-icon>

    <v-toolbar-title class="pl-0">
      CodeChecker
    </v-toolbar-title>

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
