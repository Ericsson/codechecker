import { ReportFilter } from "@cc/report-server-types";
import { getters, mutations } from "./base-filter";

const state = {
  runIds: [],
  reportFilter: new ReportFilter(),
  cmpData: null
};

export default {
  namespaced: true,

  state,
  getters,
  mutations
};
