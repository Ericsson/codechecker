import { format, parse } from "date-fns";

export default {
  data() {
    return {
      format: "yyyy-MM-dd HH:mm:ss",
    };
  },

  methods: {
    dateTimeToStr(date) {
      if (!date) return null;

      return format(date, this.format, new Date());
    },

    strToDateTime(date) {
      if (!date) return null;

      return parse(date, this.format, new Date());
    },

    // Returns Unix time.
    getUnixTime(date) {
      if (!date) return null;

      const milliseconds = Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate(),
        date.getUTCHours(),
        date.getUTCMinutes(),
        date.getUTCSeconds(),
        date.getUTCMilliseconds());

      return parseInt(milliseconds / 1000);
    }
  }
};
