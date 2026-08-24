import { createStore } from "vuex";
import { ReportFilter } from "@cc/report-server-types";
import {
  getters as filterGetters,
  mutations as filterMutations
} from "./modules/base-filter";

import auth from "./modules/auth";
import config from "./modules/config";
import error from "./modules/error";
import product from "./modules/product";
import run from "./modules/run";
import serverInfo from "./modules/server-info";
import url from "./modules/url";

export default createStore({
  state: {
    runIds: [],
    reportFilter: new ReportFilter(),
    cmpData: null
  },
  getters: filterGetters,
  mutations: filterMutations,
  modules: {
    auth,
    config,
    error,
    product,
    run,
    serverInfo,
    url
  }
});