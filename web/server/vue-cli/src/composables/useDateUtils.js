import { ref } from "vue";

import { format, parse } from "date-fns";

export function useDateUtils() {
  const dateFormat = ref("yyyy-MM-dd HH:mm:ss");

  const dateTimeToStr = date => {
    if (!date) return null;
    return format(date, dateFormat.value, new Date());
  };

  const strToDateTime = (date, formatStr = null) => {
    if (!date) return null;
    return parse(date, formatStr || dateFormat.value, new Date());
  };

  const getUnixTime = date => {
    if (!date) return null;

    const dateObj = date instanceof Date ? date : new Date(date);

    const milliseconds = Date.UTC(
      dateObj.getUTCFullYear(),
      dateObj.getUTCMonth(),
      dateObj.getUTCDate(),
      dateObj.getUTCHours(),
      dateObj.getUTCMinutes(),
      dateObj.getUTCSeconds(),
      dateObj.getUTCMilliseconds()
    );
    return parseInt(milliseconds / 1000);
  };

  const prettifyDate = date => {
    return date.split(/[.]+/)[0];
  };

  return {
    dateFormat,
    dateTimeToStr,
    strToDateTime,
    getUnixTime,
    prettifyDate
  };
}