import { handleThriftError, prodService } from "@cc-api";

import { GET_CURRENT_PRODUCT, GET_PACKAGE_VERSION } from "../actions.type";
import { SET_CURRENT_PRODUCT, SET_PACKAGE_VERSION } from "../mutations.type";

const state = {
  currentProduct: null,
  packageVersion: undefined
};

const getters = {
  currentProduct(state) {
    return state.currentProduct;
  },
  packageVersion(state) {
    return state.packageVersion;
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
  },

  [GET_PACKAGE_VERSION]({ commit }) {
    return new Promise(resolve => {
      if (state.packageVersion !== undefined)
        return resolve(state.packageVersion);

      prodService.getClient().getPackageVersion(handleThriftError(version => {
        commit(SET_PACKAGE_VERSION, version);
        resolve(version);
      }));
    });
  }
};

const mutations = {
  [SET_CURRENT_PRODUCT](state, product) {
    state.currentProduct = product;
  },
  [SET_PACKAGE_VERSION](state, version) {
    state.packageVersion = version;
  }
};

export default {
  state,
  actions,
  mutations,
  getters
};
