import { CompareData, ReportFilter } from '@cc/report-server-types';
import {
  SET_CMP_DATA,
  SET_REPORT_FILTER,
  SET_RUN_IDS
} from '../mutations.type';

const state = {
  runIds: [],
  reportFilter: new ReportFilter(),
  cmpData: null
};

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

const actions = {
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
      state.cmpData = new CompareData(params);
    } else {
      Object.assign(state.cmpData, params);
    }
  }
};

export default {
  state,
  getters,
  actions,
  mutations
};
