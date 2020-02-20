import { CompareData, DiffType } from "@cc/report-server-types";
import {
  SET_CMP_DATA,
  SET_REPORT_FILTER,
  SET_RUN_IDS
} from "../mutations.type";

const getters = {
  getRunIds(state) {
    return state.runIds;
  },
  getReportFilter(state) {
    return state.reportFilter;
  },
  getCmpData(state) {
    return state.cmpData;
  }
};

const mutations = {
  [SET_RUN_IDS](state, runIds) {
    state.runIds = runIds;
  },
  [SET_REPORT_FILTER](state, params) {
    Object.assign(state.reportFilter, params);
  },
  [SET_CMP_DATA](state, params) {
    if (!params) {
      state.cmpData = null;
    } else if (!state.cmpData) {
      state.cmpData = new CompareData({
        diffType: DiffType.NEW,
        params
      });
    } else {
      Object.assign({
        diffType: DiffType.NEW,
        ...state.cmpData,
        ...params
      });
    }
  }
};

export {
  getters,
  mutations
};
