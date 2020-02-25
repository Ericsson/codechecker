import prettifyDate from "./prettify-date";
import truncate from "./truncate";

export default {
  install(Vue) {
    Vue.filter("prettifyDate", prettifyDate);
    Vue.filter("truncate", truncate);
  }
};
