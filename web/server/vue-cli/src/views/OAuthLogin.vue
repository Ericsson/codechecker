<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="auto" class="text-center">
        <v-progress-circular
          indeterminate
          color="primary"
          size="48"
        />
        <div class="text-grey mt-4">
          Signing you in...
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";

import { LOGIN } from "@/store/actions.type";
import { ADD_ERROR, ADD_NOTIFICATION } from "@/store/mutations.type";

const route = useRoute();
const router = useRouter();
const store = useStore();

const isAuthenticated = computed(function() {
  return store.getters["isAuthenticated"];
});

onMounted(function() {
  if (isAuthenticated.value) {
    router.replace({ name: "products" });
    return;
  }
  detectCallback();
});

function detectCallback() {
  const _params = route.query;
  const _url = window.location.href;
  const _provider = route.params.provider;

  if (_params.code != null && _params.state != null) {

    store
      .dispatch(LOGIN, {
        type: "oauth",
        provider: _provider,
        url: _url
      })
      .then(() => {
        store.commit(ADD_NOTIFICATION, {
          type: "success",
          message: "Successfully logged in!"
        });

        const returnTo = localStorage.getItem("return_to");
        localStorage.removeItem("return_to");
        router.replace(returnTo || { name: "products" });
      }).catch(_err => {
        store.commit(ADD_ERROR, {
          title: "Login failed",
          message: _err.message
        });
        router.replace({ name: "login" });
      });
  }
}
</script>

<style lang="scss" scoped>
#btn-container > button {
  margin: 0 !important;
  margin-top: 10px !important;
}

#avatar {
  position: absolute;
  margin: 0 auto;
  left: 0;
  right: 0;
  top: -70px;
  width: 95px;
  height: 95px;
  border-radius: 50%;
  z-index: 9;
  padding: 15px;
  box-shadow: 0px 2px 2px rgba(0, 0, 0, 0.1);
}

#login-btn {
  font-size: 1.2em;
}
</style>
