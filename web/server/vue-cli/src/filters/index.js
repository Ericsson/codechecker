import fromUnixTime from "./from-unix-time";
import prettifyDate from "./prettify-date";
import truncate from "./truncate";

export default {
  install(Vue) {
    Vue.filter("fromUnixTime", fromUnixTime);
    Vue.filter("prettifyDate", prettifyDate);
    Vue.filter("truncate", truncate);
  }
};
