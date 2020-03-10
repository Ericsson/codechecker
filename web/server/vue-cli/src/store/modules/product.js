import { handleThriftError, prodService } from "@cc-api";

import { GET_CURRENT_PRODUCT } from "../actions.type";
import { SET_CURRENT_PRODUCT } from "../mutations.type";

const state = {
  currentProduct: null
};

const getters = {
  currentProduct(state) {
    return state.currentProduct;
  }
};

const actions = {
  [GET_CURRENT_PRODUCT]({ commit }, endpoint) {
    if (!endpoint) {
      commit(SET_CURRENT_PRODUCT, null);
      return;
    }

    return new Promise(resolve => {
      prodService.getClient().getCurrentProduct(handleThriftError(product => {
        commit(SET_CURRENT_PRODUCT, product);
        resolve(product);
      }));
    });
  }
};

const mutations = {
  [SET_CURRENT_PRODUCT](state, product) {
    state.currentProduct = product;
  }
};

export default {
  state,
  actions,
  mutations,
  getters
};
