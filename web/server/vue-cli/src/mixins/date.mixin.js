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

    strToDateTime(date, format=null) {
      if (!date) return null;


      if (!format)
        format = this.format;

      return parse(date, format, new Date());
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
