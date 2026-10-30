import { confService, handleThriftError } from "@cc-api";

import { GET_ANNOUNCEMENT } from "../actions.type";
import {
  CLEAR_SERVER_DOWN,
  SET_ANNOUNCEMENT,
  SET_SERVER_DOWN
} from "../mutations.type";

const state = {
  announcement: undefined,
  serverDown: false
};

const getters = {
  announcement(state) {
    return state.announcement;
  },
  serverDown(state) {
    return state.serverDown;
  }
};

const actions = {
  [GET_ANNOUNCEMENT]({ commit }) {
    return new Promise(resolve => {
      if (state.announcement !== undefined) {
        resolve(state.announcement);
      } else {
        confService.getClient().getNotificationBannerText(
          handleThriftError(announcement => {
            commit(SET_ANNOUNCEMENT, window.atob(announcement));
            resolve(announcement);
          }));
      }      
    });
  }
};

const mutations = {
  [SET_ANNOUNCEMENT](state, announcement) {
    state.announcement = announcement;
  },
  [SET_SERVER_DOWN](state) {
    state.serverDown = true;
  },
  [CLEAR_SERVER_DOWN](state) {
    state.serverDown = false;
  }
};

export default {
  state,
  actions,
  mutations,
  getters
};
