
import JwtService from "@/services/jwt.service";

import {
  GET_AUTH_PARAMS,
  GET_LOGGED_IN_USER,
  LOGIN,
  LOGOUT
} from "../actions.type";

import {
  PURGE_AUTH,
  SET_AUTH,
  SET_AUTH_PARAMS,
  SET_LOGGED_IN_USER
} from "../mutations.type";
import { authService } from "@cc-api";

const state = {
  currentUser: "",
  isAuthenticated: !!JwtService.getToken(),
  authParams: null
};

const getters = {
  currentUser(state) {
    return state.currentUser;
  },
  isAuthenticated(state) {
    return state.isAuthenticated;
  },
  authParams(state) {
    return state.authParams;
  }
};

const actions = {
  [GET_AUTH_PARAMS]({ commit }) {
    if (state.authParams) return state.authParams;

    return new Promise(resolve => {
      authService.getClient().getAuthParameters((err, params) => {
        commit(SET_AUTH_PARAMS, params);
        resolve(params);
      });
    });
  },

  async [GET_LOGGED_IN_USER]({ commit, dispatch }) {
    await dispatch(GET_AUTH_PARAMS);
    if (!state.authParams.requiresAuthentication) return "";

    if (state.currentUser) return state.currentUser;

    return new Promise(resolve => {
      authService.getClient().getLoggedInUser((err, loggedInUser) => {
        commit(SET_LOGGED_IN_USER, loggedInUser);
        resolve(loggedInUser);
      });
    });
  },

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
  }
};

const mutations = {
  [SET_AUTH](state, payload) {
    state.isAuthenticated = true;
    state.currentUser = payload.userName;
    JwtService.saveToken(payload.token);
  },
  [SET_AUTH_PARAMS](state, params) {
    state.authParams = params;
  },
  [SET_LOGGED_IN_USER](state, userName) {
    state.currentUser = userName;
  },
  [PURGE_AUTH](state) {
    state.isAuthenticated = false;
    state.currentUser = null;
    JwtService.destroyToken();
  }
};

export default {
  state,
  actions,
  mutations,
  getters
};
