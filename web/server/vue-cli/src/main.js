import "core-js/stable";
import "regenerator-runtime/runtime";

import "@mdi/font/css/materialdesignicons.css";
import "codemirror/lib/codemirror.css";
import "codemirror/mode/clike/clike.js";
import "splitpanes/dist/splitpanes.css";

import Vue from "vue";
import vuetify from "@/plugins/vuetify";
import VueCookie from "vue-cookie";
import { GET_AUTH_PARAMS, GET_CURRENT_PRODUCT } from "@/store/actions.type";

import router from "./router";
import store from "./store";
import filters from "./filters";

Vue.use(VueCookie);
Vue.use(filters);

import App from "./App.vue";

import { eventHub } from "@cc-api";

import "@/variables.scss";

Vue.config.productionTip = false;

// Ensure we checked auth before each page load.
router.beforeResolve((to, from, next) => {
  // Update Thrift API services on endpoint change.
  if (from.params.endpoint === undefined ||
      to.params.endpoint !== from.params.endpoint
  ) {
    eventHub.$emit("update", to.params.endpoint);
  }

  store.dispatch(GET_AUTH_PARAMS).then(() => {
    if (to.matched.some(record => record.meta.requiresAuth)) {
      if (store.getters.authParams.requiresAuthentication &&
        !store.getters.isAuthenticated
      ) {
        // Redirect the user to the login page but keep the original path to
        // redirect the user back once logged in.
        return next({
          name: "login",
          query: { "return_to": to.fullPath }
        });
      }
    }

    // Get current product.
    if (to.params.endpoint !== from.params.endpoint)
      store.dispatch(GET_CURRENT_PRODUCT, to.params.endpoint);

    next();
  });
});

new Vue({
  router,
  store,
  vuetify,
  render: h => h(App),
}).$mount("#app");
