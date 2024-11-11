import { confService, handleThriftError } from "@cc-api";

import { GET_ANNOUNCEMENT } from "../actions.type";
import { SET_ANNOUNCEMENT } from "../mutations.type";

const state = {
  announcement: undefined
};

const getters = {
  announcement(state) {
    return state.announcement;
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
  }
};

export default {
  state,
  actions,
  mutations,
  getters
};
