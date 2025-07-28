import "vuetify/styles";
import "@mdi/font/css/materialdesignicons.css";
import "splitpanes/dist/splitpanes.css";

if (!Error.captureStackTrace) {
  Error.captureStackTrace = () => {};
}

import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import store from "./store";

import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import { aliases, mdi } from "vuetify/iconsets/mdi-svg";
import { eventHub } from "@/services/api/eventHub";

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: { mdi }
  },
  defaults: {
    global: {
      density: "compact"
    }
  }
});

const pathParts = window.location.pathname.split("/");
const endpoint = pathParts[1] === "products" ? pathParts[2] : pathParts[1];
window.__cc_endpoint = endpoint;
eventHub.emit("update", endpoint);

const app = createApp(App);
app.use(router);
app.use(store);
app.use(vuetify);
app.provide("eventHub", eventHub);
app.mount("#app");
