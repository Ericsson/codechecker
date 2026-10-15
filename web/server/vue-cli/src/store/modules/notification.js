import {
  ADD_ERROR,
  ADD_NOTIFICATION,
  CLEAR_ERRORS,
  CLEAR_NOTIFICATIONS,
  REMOVE_ERROR,
  REMOVE_NOTIFICATION
} from "../mutations.type";

let nextNotificationId = 0;

const state = {
  notifications: []
};

const getters = {
  notifications(state) {
    return state.notifications;
  }
};

const actions = {
};

// Normalize a commit payload into a notification object. Accepts either a
// plain message string or an object with `message` (and optionally `title`,
// `timeout`). The `type` ("error" | "success") is supplied by the caller.
function pushNotification(state, payload, type) {
  const normalized =
    typeof payload === "string" ? { message: payload } : payload;

  state.notifications.push({
    id: nextNotificationId++,
    type,
    title: normalized.title,
    message: normalized.message,
    timeout: normalized.timeout
  });
}

const mutations = {
  [ADD_NOTIFICATION](state, notification) {
    pushNotification(state, notification, notification?.type ?? "error");
  },
  [REMOVE_NOTIFICATION](state, id) {
    state.notifications = state.notifications.filter(n => n.id !== id);
  },
  [CLEAR_NOTIFICATIONS](state) {
    state.notifications = [];
  },

  // Backward-compatible error aliases.
  [ADD_ERROR](state, error) {
    console.warn(error);
    pushNotification(state, error, "error");
  },
  [REMOVE_ERROR](state, id) {
    state.notifications = state.notifications.filter(n => n.id !== id);
  },
  [CLEAR_ERRORS](state) {
    state.notifications = [];
  },
};

export default {
  state,
  actions,
  mutations,
  getters
};
