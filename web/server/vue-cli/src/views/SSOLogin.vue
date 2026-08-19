<template>
  <v-container
    class="fill-height"
    fluid
  />
</template>

<script setup>
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";

import { GET_LOGGED_IN_USER, LOGIN } from "@/store/actions.type";
import { SET_REDIRECT } from "@/store/mutations.type";

const route = useRoute();
const router = useRouter();
const store = useStore();

onMounted(() => {
  login();
});

function login() {
  const code = route.query["code"];
  const redirect = localStorage.getItem(SET_REDIRECT);

  if (!code) {
    router.replace({
      name: "login",
      query: { error: "Failed to log in! Missing SSO login code." }
    });
    return;
  }

  store
    .dispatch(LOGIN, { type: "sso", code })
    .then(() => store.dispatch(GET_LOGGED_IN_USER))
    .then(() => {
      router.replace(redirect || { name: "products" });
      localStorage.removeItem(SET_REDIRECT);
    })
    .catch(err => {
      router.replace({
        name: "login",
        query: { error: `Failed to log in! ${err.message}` }
      });
    });
}
</script>
