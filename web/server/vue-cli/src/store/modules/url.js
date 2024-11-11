import { CLEAR_QUERIES, SET_QUERIES } from "../mutations.type";

const state = {
  queries: {}
};

const getters = {
  queries(state) {
    return state.queries;
  }
};

const mutations = {
  [CLEAR_QUERIES](state, { except }) {
    if (except) {
      Object.keys(state.queries).forEach(key => {
        if (!except.includes(key))
          delete state.queries[key];
      });
    } else {
      state.queries = {};
    }
  },

  [SET_QUERIES](state, { location, query }) {
    state.queries[location] = query;
  }
};

export default {
  state,
  mutations,
  getters
};
