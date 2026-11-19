// The timezone is fixed to Europe/Budapest by jest.global-setup.js.
import prettifyDate from "@/filters/prettify-date";

describe("prettify-date.js", () => {
  test("Prettify date", () => {
    expect(prettifyDate("2000-01-01 00:00:00"))
      .toEqual("2000-01-01 00:00:00 (UTC+01:00)");
    expect(prettifyDate("2000-01-01 00:00:00.012345"))
      .toEqual("2000-01-01 00:00:00 (UTC+01:00)");
    expect(prettifyDate("2000-06-30 22:00:00.012345+00:00"))
      .toEqual("2000-07-01 00:00:00 (UTC+02:00)");
  });
});
