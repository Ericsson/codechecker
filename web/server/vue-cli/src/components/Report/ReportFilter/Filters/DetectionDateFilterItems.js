import {
  endOfMonth,
  endOfToday,
  endOfYear,
  endOfYesterday,
  startOfMonth,
  startOfToday,
  startOfYear,
  startOfYesterday,
  subDays
} from "date-fns";

/**
 * Date types which will be added to the Date filter tooltip.
 */
const items = {
  "TODAY" : 0,
  "YESTERDAY" : 1,
  "LAST_7_DAYS" : 2,
  "THIS_MONTH" : 3,
  "THIS_YEAR" : 4
};

function titleFormatter (id) {
  switch (id) {
  case items.TODAY:
    return "Today";
  case items.YESTERDAY:
    return "Yesterday";
  case items.LAST_7_DAYS:
    return "Last 7 days";
  case items.THIS_MONTH:
    return "This month";
  case items.THIS_YEAR:
    return "This year";
  default:
    return id;
  }
}

function getDateInterval(id) {
  switch (id) {
  case items.TODAY:
    return { from : startOfToday(), to : endOfToday() };
  case items.YESTERDAY:
    return { from : startOfYesterday(), to : endOfYesterday() };
  case items.LAST_7_DAYS:
    return { from : subDays(startOfToday(), 7), to : startOfToday() };
  case items.THIS_MONTH:
    return { from : startOfMonth(new Date), to : endOfMonth(new Date) };
  case items.THIS_YEAR:
    return { from : startOfYear(new Date), to : endOfYear(new Date) };
  default:
    console.warn(`No date interval has been specified for type: ${id}`);
  }
}

export {
  items as default,
  getDateInterval,
  titleFormatter
};
