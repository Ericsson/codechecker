import prettifyDate from "@/filters/prettify-date";

describe("prettify-date.js", () => {
  test("Prettify date", () => {
    expect(prettifyDate("2000-00-00 00:00:00")).toEqual("2000-00-00 00:00:00");
    expect(prettifyDate("2000-00-00 00:00:00.012345"))
      .toEqual("2000-00-00 00:00:00");
  });
});
