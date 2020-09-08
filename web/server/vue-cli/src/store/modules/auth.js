
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
import { authService, handleThriftError } from "@cc-api";

const state = {
  currentUser: "",
  isAuthenticated: !!authService.getToken(),
  authParams: null,
  packageVersion: undefined
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
      authService.getClient().getAuthParameters(
        handleThriftError(params => {
          commit(SET_AUTH_PARAMS, params);
          resolve(params);
        }));
    });
  },

  async [GET_LOGGED_IN_USER]({ commit, dispatch }) {
    await dispatch(GET_AUTH_PARAMS);
    if (!state.authParams.requiresAuthentication) return "";

    if (state.currentUser) return state.currentUser;

    return new Promise(resolve => {
      authService.getClient().getLoggedInUser(
        handleThriftError(loggedInUser => {
          commit(SET_LOGGED_IN_USER, loggedInUser);
          resolve(loggedInUser);
        }));
    });
  },

  [LOGIN](context, credentials) {
    return new Promise((resolve, reject) => {
      authService.getClient().performLogin("Username:Password",
        `${credentials.username}:${credentials.password}`,
        handleThriftError(token => {
          context.commit(SET_AUTH, {
            userName: credentials.username,
            token: token
          });
          resolve(token);
        }, err => {
          reject(err);
        }));
    });
  },

  [LOGOUT](context) {
    return new Promise((resolve, reject) => {
      authService.getClient().destroySession(
        handleThriftError(success => {
          if (success) {
            context.commit(PURGE_AUTH);
            resolve();
          }
        }, err => {
          reject(err);
        }));
    });
  }
};

const mutations = {
  [SET_AUTH](state, payload) {
    state.isAuthenticated = true;
    state.currentUser = payload.userName;
    authService.saveToken(payload.token);
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
    authService.destroyToken();
  }
};

export default {
  state,
  actions,
  mutations,
  getters
};
