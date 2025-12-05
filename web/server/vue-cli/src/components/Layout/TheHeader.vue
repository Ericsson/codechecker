<template>
  <v-app-bar
    extension-height="24"
    color="primary"
    density="default"
  >
    <template
      v-if="announcement && announcement.length"
      v-slot:extension
    >
      <div
        class="d-flex justify-center align-center w-100"
        style="background-color: #ff9800; height: 24px; color: black;"
      >
        <v-icon>mdi-bullhorn-outline</v-icon>
        <span class="font-weight-semibold ml-2">
          {{ announcement }}
        </span>
      </div>
    </template>

    <v-app-bar-nav-icon>
      <v-avatar
        size="36px"
        :image="require('@/assets/logo.png')"
        color="transparent"
      />
    </v-app-bar-nav-icon>

    <v-toolbar-title class="pl-0">
      CodeChecker {{ packageVersion }}
      <v-chip
        v-if="currentProductDisplayName"
        class="mx-2"
        variant="outlined"
      >
        {{ currentProductDisplayName }}
      </v-chip>
    </v-toolbar-title>

    <v-spacer />

    <span
      v-if="showMenuItems"
    >
      <v-btn
        v-for="item in menuItems"
        :key="item.name"
        :to="{
          name: item.route,
          params: $route.params.endpoint ?
            { endpoint: $route.params.endpoint } : {},
          query: queries[item.query_namespace] === undefined
            ? item.query || {}
            : queries[item.query_namespace]
        }"
        :class="item.active.includes($route.name) &&
          'v-btn--active router-link-active'"
        :exact="item.exact"
        variant="text"
      >
        <v-icon class="mr-2">
          {{ item.icon }}
        </v-icon>
        {{ item.name }}
      </v-btn>
    </span>

    <v-menu
      v-if="showConfigItems"
    >
      <template v-slot:activator="{ props }">
        <v-btn
          v-bind="props"
          variant="text"
          :class="configureMenuItems.map(c => c.route).includes($route.name) &&
            'v-btn--active router-link-active'"
        >
          <v-icon class="mr-2">
            mdi-cog-outline
          </v-icon>
          Configuration
          <v-icon class="ml-2">
            mdi-menu-down
          </v-icon>
        </v-btn>
      </template>

      <v-list>
        <v-list-item
          v-for="item in configureMenuItems"
          :key="item.title"
          :to="{ 
            name: item.route,
            params: $route.params.endpoint ?
              { endpoint: $route.params.endpoint } : {}
          }"
          exact
        >
          <template v-slot:prepend>
            <v-icon class="mr-1">
              {{ item.icon }}
            </v-icon>
          </template>
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <v-divider
      v-if="showUserInfo && menuItems.length"
      class="mx-2"
      vertical
      :style="{ display: 'inline' }"
    />

    <user-info-menu
      v-if="showUserInfo"
    />

    <v-menu>
      <template v-slot:activator="{ props }">
        <v-btn
          v-bind="props"
          icon
        >
          <v-icon>mdi-dots-vertical</v-icon>
        </v-btn>
      </template>

      <header-menu-items />
    </v-menu>
  </v-app-bar>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useStore } from "vuex";

import { GET_ANNOUNCEMENT, GET_PACKAGE_VERSION } from "@/store/actions.type";

import { defaultReportFilterValues } from "@/components/Report/ReportFilter";
import { defaultStatisticsFilterValues } from "@/components/Statistics";
import HeaderMenuItems from "./HeaderMenuItems";
import UserInfoMenu from "./UserInfoMenu";

const store = useStore();
const route = useRoute();

const menuButtons = ref([
  {
    name: "Products",
    query_namespace: "products",
    icon: "mdi-briefcase-outline",
    route: "products",
    active: [ "products" ],
    exact: true,
    hide: [ "products", "login", "404" ]
  },
  {
    name: "Runs",
    query_namespace: "runs",
    icon: "mdi-run-fast",
    route: "runs",
    active: [ "runs", "main_runs" ],
    exact: true,
    hide: [ "products", "login", "404" ]
  },
  {
    name: "Reports",
    query_namespace: "report_filter",
    icon: "mdi-bug",
    route: "reports",
    active: [ "reports" ],
    exact: true,
    query: defaultReportFilterValues,
    hide: [ "products", "login", "404" ]
  },
  {
    name: "Statistics",
    query_namespace: "report_filter",
    icon: "mdi-chart-line",
    route: "statistics",
    active: [ "statistics" ],
    exact: false,
    query: defaultStatisticsFilterValues,
    hide: [ "products", "login", "404" ]
  }
]);

const configureMenuItems = ref([
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
]);

const queries = computed(() => store.getters.queries);
const authParams = computed(() => store.getters.authParams);
const isAuthenticated = computed(() => store.getters.isAuthenticated);
const announcement = computed(() => store.getters.announcement);
const packageVersion = computed(() => store.getters.packageVersion);
const currentProduct = computed(() => store.getters.currentProduct);

const currentProductDisplayName = computed(() => {
  return currentProduct.value
    ? window.atob(currentProduct.value.displayedName_b64)
    : null;
});

const menuItems = computed(() => {
  if (!route.name) return [];

  return menuButtons.value.filter(item => {
    return !item.hide || !item.hide.includes(route.name);
  });
});

const showMenuItems = computed(() => {
  return !authParams.value?.requiresAuthentication || isAuthenticated.value;
});

const showUserInfo = computed(() => {
  return authParams.value?.requiresAuthentication && isAuthenticated.value;
});

const showConfigItems = computed(() => {
  return ![ "products", "login", "404" ].includes(route.name) &&
    showMenuItems;
});

onMounted(() => {
  getAnnouncement();
  getPackageVersion();
});

const getAnnouncement = () => store.dispatch(GET_ANNOUNCEMENT);
const getPackageVersion = () => store.dispatch(GET_PACKAGE_VERSION);
</script>
