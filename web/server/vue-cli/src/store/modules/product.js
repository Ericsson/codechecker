import { handleThriftError, prodService } from "@cc-api";

import {
  GET_CURRENT_PRODUCT,
  GET_CURRENT_PRODUCT_CONFIG,
  GET_PACKAGE_VERSION
} from "../actions.type";

import {
  SET_CURRENT_PRODUCT,
  SET_CURRENT_PRODUCT_CONFIG,
  SET_PACKAGE_VERSION
} from "../mutations.type";

const state = {
  currentProduct: null,
  currentProductConfig: null,
  packageVersion: undefined
};

const getters = {
  currentProduct(state) {
    return state.currentProduct;
  },
  currentProductConfig(state) {
    return state.currentProductConfig;
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

  [GET_CURRENT_PRODUCT_CONFIG]({ commit }, productId) {
    if (!productId) {
      commit(SET_CURRENT_PRODUCT_CONFIG, null);
      return;
    }

    return new Promise(resolve => {
      prodService.getClient().getProductConfiguration(productId,
        handleThriftError(config => {
          commit(SET_CURRENT_PRODUCT_CONFIG, config);
          resolve(config);
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
  [SET_CURRENT_PRODUCT_CONFIG](state, config) {
    state.currentProductConfig = config;
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
