import { ADD_ERROR, CLEAR_ERRORS } from "../mutations.type";

const state = {
  errors: []
};

const getters = {
  errors(state) {
    return state.errors;
  }
};

const actions = {
};

const mutations = {
  [ADD_ERROR](state, error) {
    console.warn(error);
    state.errors.push(error);
  },
  [CLEAR_ERRORS](state) {
    state.errors = [];
  },
};

export default {
  state,
  actions,
  mutations,
  getters
};
