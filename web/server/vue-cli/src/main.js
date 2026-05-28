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

import { defaults } from "chart.js";

defaults.plugins.datalabels = false;

import { createApp } from "vue";

import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import { aliases, mdi } from "vuetify/iconsets/mdi";

import App from "./App.vue";

import {
  GET_AUTH_PARAMS,
  GET_CURRENT_PRODUCT,
  GET_CURRENT_PRODUCT_CONFIG
} from "@/store/actions.type";
import { CLEAR_QUERIES, SET_QUERIES } from "@/store/mutations.type";
import convertOldUrlToNew from "./router/backward-compatible-url";

import fromUnixTime from "./filters/from-unix-time";
import prettifyDate from "./filters/prettify-date";
import truncate from "./filters/truncate";

import router from "./router";
import store from "./store";

const app = createApp(App);

app.config.globalProperties.$filters = {
  fromUnixTime,
  prettifyDate,
  truncate
};

import { eventHub } from "@cc-api";

let isFirstRouterResolve = true;

// Ensure we checked auth before each page load.
router.beforeResolve((to, from, next) => {
  // Update Thrift API services on endpoint change.
  if (from.params.endpoint === undefined ||
      to.params.endpoint !== from.params.endpoint
  ) {
    eventHub.dispatchEvent(
      new CustomEvent("update", { detail: to.params.endpoint })
    );
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
        (!store.getters.authParams.sessionStillActive ||
         !store.getters.isAuthenticated)
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

  let query_namespace = to.name;
  if (to.name === "reports"
    || to.name === "product-overview"
    || to.name === "checker-statistics"
    || to.name === "severity-statistics"
    || to.name === "component-statistics"
  )
    query_namespace = "report_filter";

  store.commit(SET_QUERIES, { location: query_namespace, query: to.query });
});

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: "light",
    themes: {
      light: {
        colors: {
          primary: "#2280c3",
          secondary: "#2c87c7",
          accent: "#009688",
          error: "#f44336",
          warning: "#ff9800",
          info: "#3f51b5",
          success: "#4caf50",
          grey: "#9E9E9E"
        }
      }
    }
  }
});

app.use(router);
app.use(store);
app.use(vuetify);
app.mount("#app");
