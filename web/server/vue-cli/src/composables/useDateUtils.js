import { ref } from "vue";

import { format, isValid, parse, parseISO } from "date-fns";

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

  const prettifyDate = date => formatDateTime(date);

  return {
    dateFormat,
    dateTimeToStr,
    strToDateTime,
    getUnixTime,
    toDate,
    formatDateTime,
    prettifyDate
  };
}

// Convert a Date or an API date string to a Date. API strings look like
// "2024-07-01 12:00:00.000000+02:00". Strings without an offset come from
// older servers and are treated as local time. Returns null if the value is
// missing or invalid.
export function toDate(value) {
  if (!value) return null;

  const date = value instanceof Date ? value : parseISO(value);
  return isValid(date) ? date : null;
}

// Format a date in the browser's timezone, followed by its UTC offset, e.g.
// "2024-07-01 12:00:00 (UTC+02:00)".
export function formatDateTime(value) {
  const date = toDate(value);
  return date ? format(date, "yyyy-MM-dd HH:mm:ss '(UTC'xxx')'") : "";
}