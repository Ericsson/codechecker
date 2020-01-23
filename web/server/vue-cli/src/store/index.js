import Vue from "vue";
import Vuex from "vuex";

import auth from "./auth.module";
import report from "./modules/report";

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    auth,
    report
  }
});