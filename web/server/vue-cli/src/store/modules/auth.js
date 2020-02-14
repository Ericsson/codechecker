
import JwtService from "@/services/jwt.service";

import { CHECK_AUTH_PARAMS, LOGIN, LOGOUT } from "../actions.type";
import {
  PURGE_AUTH,
  SET_AUTH,
  SET_AUTH_PARAMS
} from "../mutations.type";
import { authService } from "@cc-api";

const state = {
  userName: {},
  isAuthenticated: !!JwtService.getToken(),
  authParams: null
};

const getters = {
  currentUser(state) {
    return state.userName;
  },
  isAuthenticated(state) {
    return state.isAuthenticated;
  },
  authParams(state) {
    return state.authParams;
  }
};

const actions = {
  [LOGIN](context, credentials) {
    return new Promise((resolve, reject) => {
      authService.getClient().performLogin("Username:Password",
      `${credentials.username}:${credentials.password}`, (err, token) => {
        if (!err) {
          context.commit(SET_AUTH, {
            userName: credentials.username,
            token: token
          });
          resolve(token);
        } else {
          reject(err);
        }
      });
    });
  },
  [LOGOUT](context) {
    return new Promise((resolve, reject) => {
      authService.getClient().destroySession((err, success) => {
        if (!err && success) {
          context.commit(PURGE_AUTH);
          resolve();
        } else {
          reject();
        }
      });
    });
  },
  [CHECK_AUTH_PARAMS](context) {
    if (state.authParams) return;

    return new Promise(resolve => {
      authService.getClient().getAuthParameters((err, params) => {
        context.commit(SET_AUTH_PARAMS, params);
        resolve();
      });
    });
  }
};

const mutations = {
  [SET_AUTH](state, payload) {
    state.isAuthenticated = true;
    state.userName = payload.userName;
    JwtService.saveToken(payload.token);
  },
  [SET_AUTH_PARAMS](state, params) {
    state.authParams = params;
  },
  [PURGE_AUTH](state) {
    state.isAuthenticated = false;
    state.userName = null;
    JwtService.destroyToken();
  }
};

export default {
  state,
  actions,
  mutations,
  getters
};
