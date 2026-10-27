import {
  buildCoverageTree,
  commonDirectory,
  coverageLevel,
  findDirectory,
  formatPercentage,
  getBreadcrumbs,
  getDirectoryItems,
  getDirectoryOfFile,
  normalizeFileCoverage,
  percentage,
  summarize,
  toCSVRows
} from "@/components/Statistics/TestCoverage/coverage-tree";

function file(fileId, filePath, linesHit, linesFound, functionsHit = 0,
  functionsFound = 0
) {
  return {
    runId: 1, fileId, filePath, linesHit, linesFound, functionsHit,
    functionsFound
  };
}

const files = [
  file(1, "/home/user/project/src/main.c", 8, 10, 2, 2),
  file(2, "/home/user/project/src/util/str.c", 1, 10, 0, 4),
  file(3, "/home/user/project/src/util/math.c", 10, 10, 3, 3),
  file(4, "/home/user/project/include/util.h", 0, 0, 0, 0)
];

describe("Test coverage helpers", () => {
  test("normalize Thrift objects", () => {
    const int64 = value => ({ toNumber: () => value });
    expect(normalizeFileCoverage({
      runId: int64(1),
      fileId: int64(2),
      filePath: "/a.c",
      linesFound: int64(10),
      linesHit: int64(5),
      functionsFound: 3,
      functionsHit: null
    })).toEqual({
      runId: 1,
      fileId: 2,
      filePath: "/a.c",
      linesFound: 10,
      linesHit: 5,
      functionsFound: 3,
      functionsHit: 0
    });
  });

  test("percentage, level and format", () => {
    expect(percentage(1, 0)).toBeNull();
    expect(percentage(1, 4)).toBe(25);

    expect(coverageLevel(null)).toBe("none");
    expect(coverageLevel(80)).toBe("high");
    expect(coverageLevel(79.9)).toBe("medium");
    expect(coverageLevel(50)).toBe("medium");
    expect(coverageLevel(49.9)).toBe("low");
    expect(coverageLevel(0)).toBe("low");

    expect(formatPercentage(null)).toBe("-");
    expect(formatPercentage(100)).toBe("100.0%");
    expect(formatPercentage(percentage(999, 1000))).toBe("99.9%");
    // Not fully covered values are never rounded up to 100%.
    expect(formatPercentage(percentage(9999, 10000))).toBe("99.9%");
    expect(formatPercentage(percentage(1, 3))).toBe("33.3%");
    expect(formatPercentage(0.29 * 100)).toBe("29.0%");
    expect(formatPercentage(percentage(29, 100))).toBe("29.0%");
  });

  test("summarize", () => {
    expect(summarize(files)).toEqual({
      linesFound: 30, linesHit: 19, functionsFound: 9, functionsHit: 5
    });
    expect(summarize([])).toEqual({
      linesFound: 0, linesHit: 0, functionsFound: 0, functionsHit: 0
    });
  });

  test("common directory", () => {
    expect(commonDirectory([])).toBe("");
    expect(commonDirectory([ "/a/b/c.c" ])).toBe("/a/b");
    expect(commonDirectory([ "/a/b/c.c", "/a/bc/d.c" ])).toBe("/a");
    expect(commonDirectory([ "/a/b.c", "/c/d.c" ])).toBe("/");
    expect(commonDirectory([ "src/a.c", "src/b/c.c" ])).toBe("src");
    expect(commonDirectory([ "a.c", "b.c" ])).toBe("");
  });

  test("tree aggregates the coverage of directories", () => {
    const root = buildCoverageTree(files);

    expect(root.path).toBe("/home/user/project");
    expect(root.linesFound).toBe(30);
    expect(root.linesHit).toBe(19);

    const util = findDirectory(root, "/home/user/project/src/util");
    expect(util).toMatchObject({
      name: "util", linesFound: 20, linesHit: 11, functionsFound: 7,
      functionsHit: 3
    });

    expect(findDirectory(root, "")).toBe(root);
    expect(findDirectory(root, "/home/user/project/src/main.c")).toBeNull();
    expect(findDirectory(root, "/home/user/projectX/src")).toBeNull();
    expect(findDirectory(root, "/other")).toBeNull();
  });

  test("directory items: directories first, then files by name", () => {
    const root = buildCoverageTree(files);
    const src = findDirectory(root, "/home/user/project/src");

    const items = getDirectoryItems(src);
    expect(items.map(item => item.name)).toEqual([ "util", "main.c" ]);
    expect(items[0]).toMatchObject({
      isFile: false, fileId: null, linePercent: 55,
      functionPercent: 300 / 7
    });
    expect(items[1]).toMatchObject({
      isFile: true, fileId: 1, path: "/home/user/project/src/main.c",
      linePercent: 80, functionPercent: 100
    });

    const include = getDirectoryItems(
      findDirectory(root, "/home/user/project/include"));
    expect(include[0].linePercent).toBeNull();

    expect(getDirectoryItems(null)).toEqual([]);
  });

  test("search in the subtree", () => {
    const root = buildCoverageTree(files);

    expect(getDirectoryItems(root, "  MATH ").map(item => item.name))
      .toEqual([ "src/util/math.c" ]);
    expect(getDirectoryItems(root, "util").map(item => item.name))
      .toEqual([ "src/util", "include/util.h" ]);
    expect(getDirectoryItems(root, "nothing")).toEqual([]);
  });

  test("relative paths", () => {
    const root = buildCoverageTree([
      file(1, "a.c", 1, 1), file(2, "lib/b.c", 0, 1)
    ]);

    expect(root.name).toBe(".");
    expect(getDirectoryItems(root).map(item => item.name))
      .toEqual([ "lib", "a.c" ]);
    expect(findDirectory(root, "lib").linesFound).toBe(1);
  });

  test("breadcrumbs", () => {
    const root = buildCoverageTree(files);

    expect(getBreadcrumbs(root, "/home/user/project/src/util")).toEqual([
      { title: "/home/user/project", path: "/home/user/project" },
      { title: "src", path: "/home/user/project/src" },
      { title: "util", path: "/home/user/project/src/util" }
    ]);
    expect(getBreadcrumbs(root, "/unknown")).toEqual([
      { title: "/home/user/project", path: "/home/user/project" }
    ]);
  });

  test("directory of a file", () => {
    expect(getDirectoryOfFile("/a/b/c.c")).toBe("/a/b");
    expect(getDirectoryOfFile("/c.c")).toBe("/");
    expect(getDirectoryOfFile("c.c")).toBe("");
  });

  test("CSV export", () => {
    const rows = toCSVRows([
      file(2, "/b\"q\".c", 0, 0), file(1, "/a.c", 1, 3, 1, 2)
    ]);

    expect(rows).toEqual([
      [
        "File", "Executed lines", "Executable lines", "Line coverage",
        "Executed functions", "Functions", "Function coverage"
      ],
      [ "\"/a.c\"", 1, 3, "33.3%", 1, 2, "50.0%" ],
      [ "\"/b\"\"q\"\".c\"", 0, 0, "-", 0, 0, "-" ]
    ]);
  });
});
