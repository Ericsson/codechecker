import "core-js/stable";
import "regenerator-runtime/runtime";

// Thrift uses captureStackTrace function which is not available in Firefox
// and it will throw an exception. For this reason we define this function as
// an empty function. There is already a patch which will solve this problem:
// https://github.com/apache/thrift/pull/2082
// If this fix is merged and we upgraded the thrift version we can remove this.
if (!Error.captureStackTrace) {
  Error.captureStackTrace = () => {};
}

import "@mdi/font/css/materialdesignicons.css";
import "splitpanes/dist/splitpanes.css";

import Chart from "chart.js";
import ChartDataLabels from "chartjs-plugin-datalabels";

Chart.plugins.unregister(ChartDataLabels);

import Vue from "vue";
import vuetify from "@/plugins/vuetify";

import {
  GET_AUTH_PARAMS,
  GET_CURRENT_PRODUCT,
  GET_CURRENT_PRODUCT_CONFIG
} from "@/store/actions.type";
import { CLEAR_QUERIES, SET_QUERIES } from "@/store/mutations.type";
import convertOldUrlToNew from "./router/backward-compatible-url";

import router from "./router";
import store from "./store";
import filters from "./filters";

Vue.use(filters);

import App from "./App.vue";

import { eventHub } from "@cc-api";

Vue.config.productionTip = false;

let isFirstRouterResolve = true;

// Ensure we checked auth before each page load.
router.beforeResolve((to, from, next) => {
  // Update Thrift API services on endpoint change.
  if (from.params.endpoint === undefined ||
      to.params.endpoint !== from.params.endpoint
  ) {
    eventHub.$emit("update", to.params.endpoint);
  }

  // To be backward compatible with the old UI url format we will convert old
  // urls to new format on the first page load.
  if (isFirstRouterResolve) {
    isFirstRouterResolve = false;
    const params = convertOldUrlToNew(to);
    if (params)
      return next(params);
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

    // Get current product and configuration.
    if (to.params.endpoint !== from.params.endpoint)
      store
        .dispatch(GET_CURRENT_PRODUCT, to.params.endpoint)
        .then(product => {
          store.dispatch(GET_CURRENT_PRODUCT_CONFIG, product?.id);
        });

    next();
  });
});

router.afterEach(to => {
  if (to.name === "products")
    store.commit(CLEAR_QUERIES, { except: [ "products" ] });

  store.commit(SET_QUERIES, { location: to.name, query: to.query });
});

new Vue({
  router,
  store,
  vuetify,
  render: h => h(App),
}).$mount("#app");
