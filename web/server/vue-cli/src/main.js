import '@mdi/font/css/materialdesignicons.css'
import 'codemirror/lib/codemirror.css';
import 'codemirror/mode/clike/clike.js';

import Vue from 'vue';
import vuetify from '@/plugins/vuetify';

import router from "./router";
import store from "./store";
import App from './App.vue';

import { eventHub } from '@cc-api/_base.service';

import "@/variables.scss";

Vue.config.productionTip = false

// Ensure we checked auth before each page load.
router.beforeResolve((to, from, next) => {
  // Update Thrift API services on endpoint change.
  if (from.params.endpoint === undefined ||
      to.params.endpoint !== from.params.endpoint
  ) {
    eventHub.$emit('update', to.params.endpoint);
  }

  if(to.matched.some(record => record.meta.requiresAuth)) {
    if (store.getters.isAuthenticated) {
      next()
      return
    }
    next('/login')
  } else {
    next()
  }
});

new Vue({
  router,
  store,
  vuetify,
  render: h => h(App),
}).$mount('#app')
