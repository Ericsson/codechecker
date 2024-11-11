import convertOldUrlToNew from "@/router/backward-compatible-url";

describe("Backward compatible urls", () => {
  test("convert url with hash but without tab and subtab properties", () => {
    const route = {
      hash: "#",
      name: "runs",
      params: {}
    };

    expect(convertOldUrlToNew(route)).toBeUndefined();
  });

  test("convert statistics page url", () => {
    const route = {
      hash: "#tab=statistics",
      name: "runs",
      params: {}
    };

    const expected = {
      name: "statistics",
      query: {},
      params: route.params
    };
    expect(convertOldUrlToNew(route)).toEqual(expected);
  });

  test("convert all reports page url", () => {
    const route = {
      hash: "#tab=allReports",
      name: "runs",
      params: {}
    };

    const expected = {
      name: "reports",
      query: {},
      params: route.params
    };
    expect(convertOldUrlToNew(route)).toEqual(expected);
  });

  test("convert runs page url", () => {
    const route = {
      hash: "#run=myrun&tab=myrun",
      name: "runs",
      params: {}
    };

    const expected = {
      name: "runs",
      query: { run: "myrun" },
      params: route.params
    };
    expect(convertOldUrlToNew(route)).toEqual(expected);
  });

  test("convert report page url", () => {
    const route = {
      hash: "#run=myrun&tab=myrun&reportHash=7d6&report=1&subtab=7d6",
      name: "runs",
      params: {}
    };

    const expected = {
      name: "report-detail",
      query: { run: "myrun", "report-hash": "7d6", "report-id": "1" },
      params: route.params
    };
    expect(convertOldUrlToNew(route)).toEqual(expected);
  });

  test("convert run history page url", () => {
    const route = {
      hash: "#tab=allReports&subtab=runHistory",
      name: "runs",
      params: {}
    };

    const expected = {
      name: "run-history",
      query: {},
      params: route.params
    };
    expect(convertOldUrlToNew(route)).toEqual(expected);
  });

  test("convert new features page url", () => {
    const route = {
      hash: "#tab=changelog",
      name: "runs",
      params: {}
    };

    const expected = {
      name: "new-features",
      query: {},
      params: route.params
    };
    expect(convertOldUrlToNew(route)).toEqual(expected);
  });

  test("convert userguide page url", () => {
    const route = {
      hash: "#tab=userguide",
      name: "runs",
      params: {}
    };

    const expected = {
      name: "userguide",
      query: {},
      params: route.params
    };
    expect(convertOldUrlToNew(route)).toEqual(expected);
  });
});
