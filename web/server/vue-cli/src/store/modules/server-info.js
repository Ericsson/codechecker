
import { handleThriftError, serverInfoService } from "@cc-api";
import { GET_PACKAGE_VERSION } from "../actions.type";
import { SET_PACKAGE_VERSION } from "../mutations.type";

const state = {
  packageVersion: undefined
};

const getters = {
  packageVersion(state) {
    return state.packageVersion;
  }
};

const actions = {
  [GET_PACKAGE_VERSION]({ commit }) {
    return new Promise(resolve => {
      if (state.packageVersion !== undefined)
        return resolve(state.packageVersion);

      serverInfoService.getClient().getPackageVersion(handleThriftError(
        version => {
          commit(SET_PACKAGE_VERSION, version);
          resolve(version);
        }));
    });
  }
};

const mutations = {
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
