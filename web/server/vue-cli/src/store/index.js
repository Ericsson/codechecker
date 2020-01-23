import Vue from "vue";
import Vuex from "vuex";

import auth from "./auth.module";
import reportfilter from "./modules/report-filter"

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    auth,
    reportfilter
  }
});