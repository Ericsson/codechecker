import { buildPageTitle, buildReportTitle } from "@/composables/usePageTitle";

describe("buildPageTitle", () => {
  test("only the suffix when nothing is given", () => {
    expect(buildPageTitle()).toEqual("CodeChecker");
    expect(buildPageTitle({})).toEqual("CodeChecker");
  });

  test("page without product", () => {
    expect(buildPageTitle({ page: "Products" }))
      .toEqual("Products - CodeChecker");
  });

  test("page with product", () => {
    expect(buildPageTitle({ page: "Runs", product: "myproj" }))
      .toEqual("Runs - myproj - CodeChecker");
  });

  test("detail comes first", () => {
    expect(buildPageTitle({
      detail: "main.cpp:42 [core.DivideZero]",
      product: "myproj"
    })).toEqual("main.cpp:42 [core.DivideZero] - myproj - CodeChecker");
  });

  test("empty parts are skipped", () => {
    expect(buildPageTitle({ detail: "", page: null, product: undefined }))
      .toEqual("CodeChecker");
  });
});

describe("buildReportTitle", () => {
  test("uses the basename of the file path", () => {
    expect(buildReportTitle("/home/user/proj/src/main.cpp", 42,
      "core.DivideZero")).toEqual("main.cpp:42 [core.DivideZero]");
  });

  test("handles Windows paths", () => {
    expect(buildReportTitle("C:\\proj\\main.cpp", 7, "x"))
      .toEqual("main.cpp:7 [x]");
  });

  test("returns null without a file path", () => {
    expect(buildReportTitle(null, 1, "x")).toBeNull();
  });
});
