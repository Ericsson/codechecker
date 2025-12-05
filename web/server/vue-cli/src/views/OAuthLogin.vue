<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-text class="px-0 pb-0">
            <alerts
              :success="success"
              success-msg="Successfully logged in!"
              :error="error"
              :error-msg="errorMsg"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";

import { LOGIN } from "@/store/actions.type";
import Alerts from "@/components/Alerts.vue";

const route = useRoute();
const router = useRouter();
const store = useStore();

const success = ref(false);
const error = ref(false);
const errorMsg = ref(null);

const isAuthenticated = computed(function() {
  return store.getters["isAuthenticated"];
});

onMounted(function() {
  if (isAuthenticated.value) {
    router.replace({ name: "products" });
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
        success.value = true;
        error.value = false;

        const _w = window.location;
        window.location.href = _w.origin + _w.pathname;
      }).catch(_err => {
        errorMsg.value = `Failed to log in! ${_err.message}`;
        error.value = true;
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