<template>
  <v-app-bar
    extension-height="24px"
    app
    color="primary"
    dark
  >
    <template
      v-if="announcement.length"
      v-slot:extension
    >
      <v-system-bar
        color="#ff9800"
        absolute
        height="24px"
        light
      >
        <v-row>
          <v-col
            class="py-0"
            align="center"
          >
            <v-icon>mdi-bullhorn-outline</v-icon>
            <span class="font-weight-bold">
              {{ announcement }}
            </span>
          </v-col>
        </v-row>
      </v-system-bar>
    </template>

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
import { confService } from "@cc-api";

export default {
  name: "TheHeader",
  data() {
    return {
      announcement: ""
    };
  },
  mounted() {
    confService.getClient().getNotificationBannerText((err, announcement) => {
      this.announcement = window.atob(announcement);
    });
  }
};
</script>
