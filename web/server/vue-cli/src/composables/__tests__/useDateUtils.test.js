// The timezone is fixed to Europe/Budapest by jest.global-setup.js.
import { useDateUtils } from "@/composables/useDateUtils";

const { formatDateTime, prettifyDate, toDate } = useDateUtils();

describe("useDateUtils.js", () => {
  test("Converts offset strings to the browser timezone", () => {
    expect(formatDateTime("2024-07-01 10:00:00.000000+00:00"))
      .toEqual("2024-07-01 12:00:00 (UTC+02:00)");
    expect(formatDateTime("2024-01-15 06:30:00.123456-05:00"))
      .toEqual("2024-01-15 12:30:00 (UTC+01:00)");
  });

  test("Treats offset-less strings from older servers as local", () => {
    expect(formatDateTime("2024-07-01 12:00:00.123456"))
      .toEqual("2024-07-01 12:00:00 (UTC+02:00)");
    expect(formatDateTime("2024-07-01 12:00:00"))
      .toEqual("2024-07-01 12:00:00 (UTC+02:00)");
  });

  test("Formats Date objects", () => {
    expect(formatDateTime(new Date(Date.UTC(2024, 6, 1, 10))))
      .toEqual("2024-07-01 12:00:00 (UTC+02:00)");
  });

  test("Returns an empty string for missing or invalid values", () => {
    expect(formatDateTime(null)).toEqual("");
    expect(formatDateTime(undefined)).toEqual("");
    expect(formatDateTime("")).toEqual("");
    expect(formatDateTime("not a date")).toEqual("");
  });

  test("prettifyDate shows the timezone", () => {
    expect(prettifyDate("2024-07-01 10:00:00.000000+00:00"))
      .toEqual("2024-07-01 12:00:00 (UTC+02:00)");
    expect(prettifyDate(null)).toEqual("");
  });

  test("toDate returns the correct instant", () => {
    expect(toDate("2024-07-01 10:00:00.000000+00:00").getTime())
      .toEqual(Date.UTC(2024, 6, 1, 10));
    expect(toDate("2024-07-01 12:00:00").getTime())
      .toEqual(Date.UTC(2024, 6, 1, 10));
    expect(toDate(null)).toBeNull();
    expect(toDate("garbage")).toBeNull();
  });
});
