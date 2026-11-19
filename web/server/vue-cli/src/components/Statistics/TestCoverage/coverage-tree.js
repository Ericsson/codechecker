// Pure helper functions of the test coverage statistics page. They do not
// depend on Vue or on the Thrift API so they can be unit tested easily.

// Coverage percentage limits of the colouring of the coverage values.
export const HIGH_COVERAGE_LIMIT = 80;
export const MEDIUM_COVERAGE_LIMIT = 50;

/**
 * The coverage metrics in the order they are shown. "found" and "hit" are
 * the names of the count properties of the file coverages, "verb" describes
 * a hit entity (e.g. "4 of 6 branches taken"). The titles are used by the
 * table and the CSV export.
 */
export const METRICS = [
  {
    id: "line",
    title: "Line",
    unit: "lines",
    verb: "executed",
    icon: "mdi-format-list-numbered",
    found: "linesFound",
    hit: "linesHit",
    foundTitle: "Executable lines",
    hitTitle: "Executed lines"
  },
  {
    id: "function",
    title: "Function",
    unit: "functions",
    verb: "executed",
    icon: "mdi-function-variant",
    found: "functionsFound",
    hit: "functionsHit",
    foundTitle: "Functions",
    hitTitle: "Executed functions"
  },
  {
    id: "region",
    title: "Region",
    unit: "regions",
    verb: "executed",
    icon: "mdi-code-braces",
    found: "regionsFound",
    hit: "regionsHit",
    foundTitle: "Regions",
    hitTitle: "Executed regions"
  },
  {
    id: "branch",
    title: "Branch",
    unit: "branches",
    verb: "taken",
    icon: "mdi-source-branch",
    found: "branchesFound",
    hit: "branchesHit",
    foundTitle: "Branches",
    hitTitle: "Taken branches"
  },
  {
    id: "mcdc",
    title: "MC/DC",
    unit: "conditions",
    verb: "covered",
    icon: "mdi-call-split",
    found: "mcdcFound",
    hit: "mcdcHit",
    foundTitle: "MC/DC conditions",
    hitTitle: "Covered MC/DC conditions"
  }
];

// The line coverage is always shown, the other metrics only if they were
// measured.
const ALWAYS_SHOWN_METRICS = new Set([ "line" ]);

function toNumber(value) {
  if (value === null || value === undefined)
    return 0;

  // Thrift i64 values are Int64 objects.
  if (typeof value.toNumber === "function")
    return value.toNumber();

  return Number(value);
}

/**
 * Converts a FileCoverage Thrift object to a plain object with numbers.
 */
export function normalizeFileCoverage(fileCoverage) {
  const result = {
    runId: toNumber(fileCoverage.runId),
    fileId: toNumber(fileCoverage.fileId),
    filePath: fileCoverage.filePath
  };
  METRICS.forEach(metric => {
    result[metric.found] = toNumber(fileCoverage[metric.found]);
    result[metric.hit] = toNumber(fileCoverage[metric.hit]);
  });
  return result;
}

/**
 * Returns the metrics which should be shown for the given summed counts.
 * A metric which was not measured (e.g. region coverage of LCOV data) is
 * hidden.
 */
export function getShownMetrics(counts) {
  return METRICS.filter(metric =>
    ALWAYS_SHOWN_METRICS.has(metric.id) || counts?.[metric.found] > 0);
}

/**
 * Returns the coverage percentage or null if there is nothing to cover.
 */
export function percentage(hit, found) {
  if (!found)
    return null;

  return hit * 100 / found;
}

/**
 * Returns the coverage level ("high", "medium", "low") of the given
 * percentage or "none" if the percentage is not available.
 */
export function coverageLevel(percent) {
  if (percent === null || percent === undefined)
    return "none";

  if (percent >= HIGH_COVERAGE_LIMIT)
    return "high";

  if (percent >= MEDIUM_COVERAGE_LIMIT)
    return "medium";

  return "low";
}

/**
 * Formats the given percentage. The value is truncated (not rounded) so that
 * a not fully covered entity is never shown as 100%.
 */
export function formatPercentage(percent) {
  if (percent === null || percent === undefined)
    return "-";

  // The epsilon compensates floating point errors (e.g. 28.999999999999996).
  return `${(Math.floor(percent * 10 + 1e-9) / 10).toFixed(1)}%`;
}

function emptyCounts() {
  const counts = {};
  METRICS.forEach(metric => {
    counts[metric.found] = 0;
    counts[metric.hit] = 0;
  });
  return counts;
}

function addCounts(target, source) {
  METRICS.forEach(metric => {
    target[metric.found] += source[metric.found] || 0;
    target[metric.hit] += source[metric.hit] || 0;
  });
}

/**
 * Returns the summed coverage counts of the given files.
 */
export function summarize(files) {
  const counts = emptyCounts();
  files.forEach(file => addCounts(counts, file));
  return counts;
}

function splitPath(path) {
  return path.split("/").filter(part => part.length);
}

/**
 * Returns the longest common directory of the given file paths. The result
 * starts with "/" if every path is absolute.
 */
export function commonDirectory(paths) {
  if (!paths.length)
    return "";

  const parts = paths.map(path => splitPath(path).slice(0, -1));
  let common = parts[0];
  parts.slice(1).forEach(dirs => {
    let i = 0;
    while (i < common.length && i < dirs.length && common[i] === dirs[i])
      ++i;
    common = common.slice(0, i);
  });

  const isAbsolute = paths.every(path => path.startsWith("/"));
  return (isAbsolute ? "/" : "") + common.join("/");
}

function joinPath(dir, name) {
  if (!dir)
    return name;
  return dir.endsWith("/") ? dir + name : `${dir}/${name}`;
}

function createDirectory(name, path) {
  return { name, path, isFile: false, children: new Map(), ...emptyCounts() };
}

/**
 * Builds a directory tree from the given (normalized) file coverages. Every
 * node contains the summed coverage counts of the files below it. The root
 * of the tree is the common directory of the files.
 */
export function buildCoverageTree(files) {
  const rootPath = commonDirectory(files.map(file => file.filePath));
  const root = createDirectory(rootPath || ".", rootPath);
  const rootDepth = splitPath(rootPath).length;

  files.forEach(file => {
    const parts = splitPath(file.filePath).slice(rootDepth);
    const fileName = parts.pop();

    let node = root;
    addCounts(node, file);

    parts.forEach(part => {
      if (!node.children.has(part)) {
        node.children.set(
          part, createDirectory(part, joinPath(node.path, part)));
      }
      node = node.children.get(part);
      addCounts(node, file);
    });

    node.children.set(fileName, {
      ...file,
      name: fileName,
      path: file.filePath,
      isFile: true
    });
  });

  return root;
}

// Returns the path components of the given path relative to the root, or
// null if the path is not below the root.
function relativeParts(root, path) {
  if (!path.startsWith(root.path))
    return null;

  const rest = path.slice(root.path.length);
  if (root.path && !root.path.endsWith("/") && rest && !rest.startsWith("/"))
    return null;

  return splitPath(rest);
}

/**
 * Returns the directory node of the given path or null if it does not exist.
 * An empty path means the root directory.
 */
export function findDirectory(root, path) {
  if (!path || path === root.path)
    return root;

  const parts = relativeParts(root, path);
  if (!parts)
    return null;

  let node = root;
  for (const part of parts) {
    node = node.children.get(part);
    if (!node || node.isFile)
      return null;
  }

  return node;
}

/**
 * Returns the name of the percentage property of the table items of the
 * given metric (e.g. "linePercent").
 */
export function percentKey(metric) {
  return `${metric.id}Percent`;
}

function toItem(node, name) {
  const item = {
    name,
    path: node.path,
    isFile: node.isFile,
    fileId: node.isFile ? node.fileId : null
  };
  METRICS.forEach(metric => {
    item[metric.found] = node[metric.found];
    item[metric.hit] = node[metric.hit];
    item[percentKey(metric)] =
      percentage(node[metric.hit], node[metric.found]);
  });
  return item;
}

function compareItems(a, b) {
  if (a.isFile !== b.isFile)
    return a.isFile ? 1 : -1;
  return a.name.localeCompare(b.name);
}

/**
 * Returns the table items of the given directory node. If a search text is
 * given, every file and directory below the node whose name contains the
 * text is returned (case-insensitively) with its path relative to the node.
 */
export function getDirectoryItems(node, search) {
  if (!node)
    return [];

  const query = (search || "").trim().toLowerCase();
  if (!query) {
    return [ ...node.children.values() ]
      .map(child => toItem(child, child.name))
      .sort(compareItems);
  }

  const items = [];
  const visit = (current, prefix) => {
    current.children.forEach(child => {
      const relativePath = prefix ? `${prefix}/${child.name}` : child.name;
      if (child.name.toLowerCase().includes(query))
        items.push(toItem(child, relativePath));
      if (!child.isFile)
        visit(child, relativePath);
    });
  };
  visit(node, "");

  return items.sort(compareItems);
}

/**
 * Returns the breadcrumb items from the root to the given directory node.
 */
export function getBreadcrumbs(root, path) {
  const items = [ { title: root.name, path: root.path } ];
  const node = findDirectory(root, path);
  if (!node || node === root)
    return items;

  let current = root;
  relativeParts(root, node.path).forEach(part => {
    current = current.children.get(part);
    items.push({ title: part, path: current.path });
  });

  return items;
}

/**
 * Returns the directory of the given file path.
 */
export function getDirectoryOfFile(filePath) {
  const index = filePath.lastIndexOf("/");
  if (index === -1)
    return "";
  return index === 0 ? "/" : filePath.slice(0, index);
}

/**
 * Returns the rows (with a header) of the CSV export of the given files.
 * Every metric is exported, even if it was not measured.
 */
export function toCSVRows(files) {
  const quote = value => `"${String(value).replace(/"/g, "\"\"")}"`;

  return [
    [
      "File",
      ...METRICS.flatMap(metric => [
        metric.hitTitle, metric.foundTitle, `${metric.title} coverage`
      ])
    ],
    ...[ ...files ]
      .sort((a, b) => a.filePath.localeCompare(b.filePath))
      .map(file => [
        quote(file.filePath),
        ...METRICS.flatMap(metric => [
          file[metric.hit] || 0,
          file[metric.found] || 0,
          formatPercentage(percentage(file[metric.hit], file[metric.found]))
        ])
      ])
  ];
}
