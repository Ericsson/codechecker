import { CompareData } from '@cc/report-server-types';
import { SET_CMP_DATA } from '../mutations.type';

const state = {
  cmpData: null
};

const getters = {
  getCmpData(state) {
    return state.cmpData;
  }
};

const actions = {
};

const mutations = {
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
