import truncate from "@/filters/truncate";

describe("truncate.js", () => {
  test("no truncate", () => {
    expect(truncate("")).toEqual("");
    expect(truncate("bug", 5)).toEqual("bug");
  });

  test("truncate to the given size", () => {
    expect(truncate("codechecker", 5)).toEqual("codec...");
    expect(truncate("codechecker", 5, "###")).toEqual("codec###");
  });
});
