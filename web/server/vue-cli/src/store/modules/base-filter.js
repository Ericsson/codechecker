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
    // If only the diff type is set we will return with null to identify that
    // no compare data is set.
    if (state.cmpData && !state.cmpData.runIds && !state.cmpData.runTag &&
        !state.cmpData.openReportsDate
    ) {
      return null;
    }

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
        ...params
      });
    } else {
      Object.assign(state.cmpData, params);
    }
  }
};

export {
  getters,
  mutations
};
