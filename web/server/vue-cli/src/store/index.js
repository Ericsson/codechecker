import Vue from "vue";
import Vuex from "vuex";

import auth from "./modules/auth";

import report from "./modules/report";
import statistics from "./modules/statistics";

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    auth,
    report,
    statistics
  }
});