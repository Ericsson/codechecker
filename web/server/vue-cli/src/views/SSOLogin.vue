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

import { SSO_LOGIN } from "@/store/actions.type";
import { SET_REDIRECT } from "@/store/mutations.type";

const route = useRoute();
const router = useRouter();
const store = useStore();

onMounted(() => {
  login();
});

function login() {
  const username = route.query["username"];
  const token = route.query["token"];
  const redirect = localStorage.getItem(SET_REDIRECT);

  store
    .dispatch(SSO_LOGIN, { username, token })
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
