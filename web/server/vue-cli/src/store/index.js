import Vue from "vue";
import Vuex from "vuex";

import auth from "./modules/auth";
import report from "./modules/report";

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    auth,
    report
  }
});