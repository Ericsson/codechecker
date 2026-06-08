import fromUnixTime from "./from-unix-time";
import prettifyDate from "./prettify-date";
import truncate from "./truncate";

export default {
  install(app) {
    app.config.globalProperties.$filters = {
      fromUnixTime,
      prettifyDate,
      truncate
    };
  }
};
