import Vue from 'vue'

import App from './App.vue'
import router from "./router";
import store from "./store";

Vue.config.productionTip = false

// Ensure we checked auth before each page load.
router.beforeEach((to, from, next) => {
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
  render: h => h(App),
}).$mount('#app')
