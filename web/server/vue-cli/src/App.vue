<template>
  <v-app id="app">
    <TheHeader />

    <v-main class="d-flex flex-column">
      <router-view v-slot="{ Component }">
        <keep-alive :include="keepAliveList">
          <component :is="Component" />
        </keep-alive>
      </router-view>
      <Errors />
    </v-main>
  </v-app>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useStore } from "vuex";
import Errors from "@/components/Errors";
import { TheHeader } from "@/components/Layout";

const keepAliveList = ref([]);
const store = useStore();
const isAuthenticated = computed(() => store.getters.isAuthenticated);

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
