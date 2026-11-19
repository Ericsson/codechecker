<template>
  <v-app id="app">
    <TheHeader />

    <v-main class="d-flex flex-column">
      <router-view v-slot="{ Component }">
        <keep-alive :include="keepAliveList">
          <component :is="Component" />
        </keep-alive>
      </router-view>
      <Notifications />
    </v-main>
  </v-app>
</template>

<script setup>
import { computed, ref, watch, watchEffect } from "vue";
import { useRoute } from "vue-router";
import { useStore } from "vuex";
import Notifications from "@/components/Notifications";
import { TheHeader } from "@/components/Layout";
import { buildPageTitle, usePageTitle } from "@/composables/usePageTitle";

const keepAliveList = ref([]);
const route = useRoute();
const store = useStore();
const { pageTitleDetail } = usePageTitle();
const isAuthenticated = computed(() => store.getters.isAuthenticated);
const currentProduct = computed(() => store.getters.currentProduct);

// The current product is loaded asynchronously after the navigation, so the
// title is updated whenever the route, the product or the detail changes.
watchEffect(() => {
  document.title = buildPageTitle({
    detail: pageTitleDetail.value,
    page: route.meta.title,
    product: currentProduct.value
      ? window.atob(currentProduct.value.displayedName_b64)
      : null
  });
});

watch(isAuthenticated, newValue => {
  if (newValue) {
    keepAliveList.value.push("Products");
  } else {
    keepAliveList.value = [];
  }
});
</script>

<style lang="scss">
html {
  overflow-y: auto;
}

html, body {
  height: 100%;
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
