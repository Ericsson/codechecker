
import JwtService from "@/services/jwt.service";

import { CHECK_AUTH, LOGIN, LOGOUT } from "../actions.type";
import { SET_AUTH, PURGE_AUTH, SET_ERROR } from "../mutations.type";

const state = {
  errors: null,
  user: {},
  isAuthenticated: !!JwtService.getToken()
};

const getters = {
  currentUser(state) {
    return state.user;
  },
  isAuthenticated(state) {
    return state.isAuthenticated;
  }
};

const actions = {
  [LOGIN](context, credentials) {
    return new Promise(resolve => {
      // TODO: get data from Thrift and handler errors.
      credentials;
      const data = { user: "test" };

      context.commit(SET_AUTH, data.user);
      resolve(data);
    });
  },
  [LOGOUT](context) {
    context.commit(PURGE_AUTH);
  },
  [CHECK_AUTH](context) {
    if (JwtService.getToken()) {
      return new Promise(resolve => {
        // TODO: get data from Thrift and handler errors.
        const data = { user: "test" };

        context.commit(SET_AUTH, data.user);
        resolve(data);
      });
    } else {
      context.commit(PURGE_AUTH);
    }
  }
};

const mutations = {
  [SET_ERROR](state, error) {
    state.errors = error;
  },
  [SET_AUTH](state, user) {
    state.isAuthenticated = true;
    state.user = user;
    state.errors = {};
    JwtService.saveToken(state.user.token);
  },
  [PURGE_AUTH](state) {
    state.isAuthenticated = false;
    state.user = {};
    state.errors = {};
    JwtService.destroyToken();
  }
};

export default {
  state,
  actions,
  mutations,
  getters
};
