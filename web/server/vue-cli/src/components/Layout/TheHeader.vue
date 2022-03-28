<template>
  <v-app-bar
    extension-height="24px"
    app
    color="primary"
    dark
  >
    <template
      v-if="announcement && announcement.length"
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
      CodeChecker {{ packageVersion }}
    </v-toolbar-title>

    <v-chip
      v-if="currentProductDisplayName"
      class="mx-2"
      outlined
    >
      {{ currentProductDisplayName }}
    </v-chip>

    <v-spacer />

    <span
      v-if="showMenuItems"
    >
      <v-btn
        v-for="item in menuItems"
        :key="item.name"
        :to="{
          name: item.route,
          query: queries[item.route] === undefined
            ? item.query || {}
            : queries[item.route]
        }"
        :class="item.active.includes($route.name) &&
          'v-btn--active router-link-active'"
        :exact="item.exact"
        text
      >
        <v-icon left>
          {{ item.icon }}
        </v-icon>
        {{ item.name }}
      </v-btn>
    </span>

    <v-menu
      v-if="showConfigItems"
      offset-y
    >
      <template v-slot:activator="{ on, attrs }">
        <v-btn
          text
          :class="configureMenuItems.map(c => c.route).includes($route.name) &&
            'v-btn--active router-link-active'"
          v-bind="attrs"
          v-on="on"
        >
          <v-icon left>
            mdi-cog-outline
          </v-icon>
          Configuration
          <v-icon right>
            mdi-menu-down
          </v-icon>
        </v-btn>
      </template>

      <v-list>
        <v-list-item-group color="primary">
          <v-list-item
            v-for="item in configureMenuItems"
            :key="item.title"
            :to="{ name: item.route }"
            exact
          >
            <v-list-item-avatar class="mr-1">
              <v-icon>{{ item.icon }}</v-icon>
            </v-list-item-avatar>
            <v-list-item-title>{{ item.title }}</v-list-item-title>
          </v-list-item>
        </v-list-item-group>
      </v-list>
    </v-menu>

    <v-divider
      v-if="showUserInfo && menuItems.length"
      class="mx-2"
      inset
      vertical
      :style="{ display: 'inline' }"
    />

    <user-info-menu
      v-if="showUserInfo"
    />

    <v-menu offset-y>
      <template v-slot:activator="{ on }">
        <v-btn
          icon
          v-on="on"
        >
          <v-icon>mdi-dots-vertical</v-icon>
        </v-btn>
      </template>

      <header-menu-items />
    </v-menu>
  </v-app-bar>
</template>

<script>
import { mapActions, mapGetters } from "vuex";

import { GET_ANNOUNCEMENT, GET_PACKAGE_VERSION } from "@/store/actions.type";

import { defaultReportFilterValues } from "@/components/Report/ReportFilter";
import { defaultStatisticsFilterValues } from "@/components/Statistics";
import HeaderMenuItems from "./HeaderMenuItems";
import UserInfoMenu from "./UserInfoMenu";

export default {
  name: "TheHeader",
  components: {
    HeaderMenuItems,
    UserInfoMenu
  },
  data() {
    return {
      menuButtons: [
        {
          name: "Products",
          icon: "mdi-briefcase-outline",
          route: "products",
          active: [ "products" ],
          exact: true,
          hide: [ "products", "login", "404" ]
        },
        {
          name: "Runs",
          icon: "mdi-run-fast",
          route: "runs",
          active: [ "runs", "main_runs" ],
          exact: true,
          hide: [ "products", "login", "404" ]
        },
        {
          name: "Reports",
          icon: "mdi-bug",
          route: "reports",
          active: [ "reports" ],
          exact: true,
          query: defaultReportFilterValues,
          hide: [ "products", "login", "404" ]
        },
        {
          name: "Statistics",
          icon: "mdi-chart-line",
          route: "statistics",
          active: [ "statistics" ],
          exact: false,
          query: defaultStatisticsFilterValues,
          hide: [ "products", "login", "404" ]
        }
      ],
      configureMenuItems: [
        {
          title: "Cleanup Plan",
          icon: "mdi-sign-direction",
          route: "cleanup-plan"
        },
        {
          title: "Review Status Rules",
          icon: "mdi-format-list-checkbox",
          route: "review-status-rules"
        },
        {
          title: "Source Component",
          icon: "mdi-puzzle-outline",
          route: "source-component"
        }
      ]
    };
  },

  computed: {
    ...mapGetters([
      "queries",
      "authParams",
      "isAuthenticated",
      "announcement",
      "packageVersion",
      "currentProduct"
    ]),

    currentProductDisplayName() {
      return this.currentProduct
        ? window.atob(this.currentProduct.displayedName_b64)
        : null;
    },

    menuItems() {
      if (!this.$route.name) return [];

      return this.menuButtons.filter(item => {
        return !item.hide || !item.hide.includes(this.$route.name);
      });
    },

    showMenuItems() {
      return !this.authParams?.requiresAuthentication || this.isAuthenticated;
    },

    showUserInfo() {
      return this.authParams?.requiresAuthentication && this.isAuthenticated;
    },

    showConfigItems() {
      return ![ "products", "login", "404" ].includes(this.$route.name) &&
        this.showMenuItems;
    }
  },

  mounted() {
    this.getAnnouncement();
    this.getPackageVersion();
  },

  methods: {
    ...mapActions([
      GET_ANNOUNCEMENT,
      GET_PACKAGE_VERSION
    ])
  }
};
</script>
