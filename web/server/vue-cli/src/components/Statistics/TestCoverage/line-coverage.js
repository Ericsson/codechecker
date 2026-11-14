import { RangeSetBuilder, StateEffect, StateField } from "@codemirror/state";
import {
  Decoration,
  EditorView,
  GutterMarker,
  gutter
} from "@codemirror/view";

export const COVERED = "covered";
export const UNCOVERED = "uncovered";

const STATUS_TITLE = {
  [COVERED]: "Executed line",
  [UNCOVERED]: "Executable line which was not executed"
};

const STATUS_ICON = {
  [COVERED]: "mdi-check",
  [UNCOVERED]: "mdi-close"
};

// Branch coverage levels of a line.
export const BRANCH_FULL = "full";
export const BRANCH_PARTIAL = "partial";
export const BRANCH_NONE = "none";

/**
 * Effect which sets the coverage of the document. Its value is an object
 * with the following optional properties:
 *  - coveredLines, uncoveredLines: arrays of 1-based line numbers.
 *  - lineBranches: array of { line, hit, found } objects (taken branches).
 *  - lineMcdc: array of { line, hit, found, uncoveredConditions } objects.
 *  - uncoveredRegions: array of { startLine, startCol, endLine, endCol }
 *    objects (1-based, the end column is exclusive).
 */
export const setLineCoverage = StateEffect.define();

/**
 * Returns a map from line numbers to coverage status. If a line is listed as
 * both covered and uncovered it is considered covered.
 */
export function getLineStatuses({ coveredLines = [], uncoveredLines = [] }) {
  const statuses = new Map();
  uncoveredLines.forEach(line => statuses.set(Number(line), UNCOVERED));
  coveredLines.forEach(line => statuses.set(Number(line), COVERED));
  return statuses;
}

/**
 * Returns the branch level of the given hit and found counts.
 */
export function branchLevel(hit, found) {
  if (hit >= found)
    return BRANCH_FULL;
  return hit > 0 ? BRANCH_PARTIAL : BRANCH_NONE;
}

/**
 * Returns a map from line numbers to the branch and MC/DC coverage of the
 * lines: { branchHit, branchFound, mcdcHit, mcdcFound, uncoveredConditions,
 * level }. The level is "full" if every branch was taken and every condition
 * was covered, "none" if none of them, "partial" otherwise.
 */
export function getBranchStatuses({ lineBranches = [], lineMcdc = [] }) {
  const statuses = new Map();
  const get = line => {
    if (!statuses.has(line)) {
      statuses.set(line, {
        branchHit: 0, branchFound: 0, mcdcHit: 0, mcdcFound: 0,
        uncoveredConditions: []
      });
    }
    return statuses.get(line);
  };

  lineBranches.forEach(({ line, hit, found }) => {
    const status = get(Number(line));
    status.branchHit += Number(hit);
    status.branchFound += Number(found);
  });

  lineMcdc.forEach(({ line, hit, found, uncoveredConditions }) => {
    const status = get(Number(line));
    status.mcdcHit += Number(hit);
    status.mcdcFound += Number(found);
    status.uncoveredConditions.push(...(uncoveredConditions || []));
  });

  statuses.forEach((status, line) => {
    const levels = [];
    if (status.branchFound)
      levels.push(branchLevel(status.branchHit, status.branchFound));
    if (status.mcdcFound)
      levels.push(branchLevel(status.mcdcHit, status.mcdcFound));

    if (!levels.length) {
      statuses.delete(line);
      return;
    }

    // The line is fully covered only if both the branches and the MC/DC
    // conditions are, and uncovered only if none of them were covered.
    if (levels.every(level => level === BRANCH_FULL))
      status.level = BRANCH_FULL;
    else if (levels.every(level => level === BRANCH_NONE))
      status.level = BRANCH_NONE;
    else
      status.level = BRANCH_PARTIAL;
  });

  return statuses;
}

/**
 * Returns the tooltip text of the branch marker of a line.
 */
export function getBranchTitle(status) {
  const lines = [];
  if (status.branchFound)
    lines.push(`Branches: ${status.branchHit} / ${status.branchFound} taken`);
  if (status.mcdcFound) {
    lines.push(`MC/DC: ${status.mcdcHit} / ${status.mcdcFound} conditions ` +
      "covered");
  }
  if (status.uncoveredConditions.length) {
    lines.push("Uncovered conditions: " +
      status.uncoveredConditions.join(", "));
  }
  return lines.join("\n");
}

/**
 * Converts the given 1-based line and column to a document position. The
 * position is clamped into the document, null is returned if the line is not
 * in the document.
 */
function toPosition(doc, line, column) {
  if (line < 1 || line > doc.lines)
    return null;

  const docLine = doc.line(line);
  return Math.min(docLine.from + Math.max(column - 1, 0), docLine.to);
}

/**
 * Returns the document ranges ({ from, to }) of the given uncovered regions.
 * Empty ranges and regions outside of the document are skipped. Overlapping
 * and nested ranges are merged, so their highlights do not stack.
 */
export function getRegionRanges(regions, doc) {
  const ranges = [];
  (regions || []).forEach(region => {
    const from = toPosition(
      doc, Number(region.startLine), Number(region.startCol));
    const to = toPosition(
      doc, Number(region.endLine), Number(region.endCol));
    if (from !== null && to !== null && from < to)
      ranges.push({ from, to });
  });
  ranges.sort((a, b) => a.from - b.from || a.to - b.to);

  const merged = [];
  ranges.forEach(range => {
    const last = merged[merged.length - 1];
    if (last && range.from <= last.to)
      last.to = Math.max(last.to, range.to);
    else
      merged.push({ ...range });
  });
  return merged;
}

const regionDecoration =
  Decoration.mark({ class: "cc-coverage-region-uncovered" });

function buildRegionDecorations(regions, doc) {
  return Decoration.set(getRegionRanges(regions, doc).map(
    ({ from, to }) => regionDecoration.range(from, to)), true);
}

const lineDecorations = {
  [COVERED]: Decoration.line({ class: "cc-coverage-line-covered" }),
  [UNCOVERED]: Decoration.line({ class: "cc-coverage-line-uncovered" })
};

function buildDecorations(statuses, doc) {
  const builder = new RangeSetBuilder();
  [ ...statuses.keys() ]
    .filter(line => line >= 1 && line <= doc.lines)
    .sort((a, b) => a - b)
    .forEach(line => {
      const from = doc.line(line).from;
      builder.add(from, from, lineDecorations[statuses.get(line)]);
    });
  return builder.finish();
}

/**
 * State field which holds the coverage status of the lines and the line
 * decorations built from them. The decorations are built once, CodeMirror
 * renders only the visible ones, so large files are handled efficiently.
 */
export const lineCoverageField = StateField.define({
  create() {
    return {
      statuses: new Map(),
      branches: new Map(),
      decorations: Decoration.none,
      regionDecorations: Decoration.none
    };
  },
  update(value, tr) {
    for (const effect of tr.effects) {
      if (effect.is(setLineCoverage)) {
        const data = effect.value || {};
        const statuses = getLineStatuses(data);
        return {
          statuses,
          branches: getBranchStatuses(data),
          decorations: buildDecorations(statuses, tr.state.doc),
          regionDecorations: buildRegionDecorations(
            data.uncoveredRegions, tr.state.doc)
        };
      }
    }

    if (tr.docChanged) {
      return {
        ...value,
        decorations: value.decorations.map(tr.changes),
        regionDecorations: value.regionDecorations.map(tr.changes)
      };
    }

    return value;
  },
  provide: field => [
    EditorView.decorations.from(field, value => value.decorations),
    EditorView.decorations.from(field, value => value.regionDecorations)
  ]
});

class CoverageMarker extends GutterMarker {
  constructor(status) {
    super();
    this.status = status;
  }

  eq(other) {
    return other.status === this.status;
  }

  toDOM() {
    const marker = document.createElement("span");
    marker.className = "cc-coverage-marker mdi " + STATUS_ICON[this.status] +
      ` cc-coverage-marker-${this.status}`;
    marker.title = STATUS_TITLE[this.status];
    marker.setAttribute("role", "img");
    marker.setAttribute("aria-label", STATUS_TITLE[this.status]);
    return marker;
  }
}

const markers = {
  [COVERED]: new CoverageMarker(COVERED),
  [UNCOVERED]: new CoverageMarker(UNCOVERED)
};

const BRANCH_LEVEL_LABEL = {
  [BRANCH_FULL]: "All branches taken",
  [BRANCH_PARTIAL]: "Partially taken branches",
  [BRANCH_NONE]: "No branch taken"
};

class BranchMarker extends GutterMarker {
  constructor(status) {
    super();
    this.status = status;
    this.title = getBranchTitle(status);
  }

  eq(other) {
    return other.status.level === this.status.level &&
      other.title === this.title;
  }

  toDOM() {
    const marker = document.createElement("span");
    marker.className = "cc-coverage-branch-marker mdi mdi-source-branch " +
      `cc-coverage-branch-${this.status.level}`;
    marker.title = this.title;
    marker.setAttribute("role", "img");
    marker.setAttribute("aria-label",
      `${BRANCH_LEVEL_LABEL[this.status.level]}. ${this.title}`);
    return marker;
  }
}

const branchSpacer = new BranchMarker({
  level: BRANCH_FULL, branchHit: 0, branchFound: 0, mcdcHit: 0,
  mcdcFound: 0, uncoveredConditions: []
});

// The markers are created once per coverage data, so the gutter does not
// create new DOM elements on every scroll.
const branchMarkerCache = new WeakMap();

function getBranchMarker(status) {
  if (!branchMarkerCache.has(status))
    branchMarkerCache.set(status, new BranchMarker(status));
  return branchMarkerCache.get(status);
}

const branchGutter = gutter({
  class: "cc-coverage-branch-gutter",
  lineMarker(view, line) {
    const lineNumber = view.state.doc.lineAt(line.from).number;
    const status =
      view.state.field(lineCoverageField).branches.get(lineNumber);
    return status ? getBranchMarker(status) : null;
  },
  lineMarkerChange: update => update.transactions.some(
    tr => tr.effects.some(effect => effect.is(setLineCoverage))),
  initialSpacer: () => branchSpacer
});

const coverageGutter = gutter({
  class: "cc-coverage-gutter",
  lineMarker(view, line) {
    const lineNumber = view.state.doc.lineAt(line.from).number;
    const status =
      view.state.field(lineCoverageField).statuses.get(lineNumber);
    return status ? markers[status] : null;
  },
  lineMarkerChange: update => update.transactions.some(
    tr => tr.effects.some(effect => effect.is(setLineCoverage))),
  initialSpacer: () => markers[UNCOVERED]
});

// The colours come from the Vuetify theme so they follow theme changes.
const coverageTheme = EditorView.baseTheme({
  ".cc-coverage-line-covered": {
    backgroundColor: "rgba(var(--v-theme-success), 0.15)"
  },
  ".cc-coverage-line-uncovered": {
    backgroundColor: "rgba(var(--v-theme-error), 0.15)"
  },
  ".cc-coverage-gutter .cm-gutterElement": {
    padding: "0 4px"
  },
  ".cc-coverage-marker": {
    fontSize: "14px"
  },
  ".cc-coverage-marker-covered": {
    color: "rgb(var(--v-theme-success))"
  },
  ".cc-coverage-marker-uncovered": {
    color: "rgb(var(--v-theme-error))"
  },
  ".cc-coverage-branch-gutter .cm-gutterElement": {
    padding: "0 2px"
  },
  ".cc-coverage-branch-marker": {
    fontSize: "14px",
    cursor: "help"
  },
  ".cc-coverage-branch-full": {
    color: "rgb(var(--v-theme-success))"
  },
  ".cc-coverage-branch-partial": {
    color: "rgb(var(--v-theme-warning))"
  },
  ".cc-coverage-branch-none": {
    color: "rgb(var(--v-theme-error))"
  },
  ".cc-coverage-region-uncovered": {
    backgroundColor: "rgba(var(--v-theme-error), 0.3)",
    textDecoration: "underline wavy rgb(var(--v-theme-error))",
    textDecorationSkipInk: "none"
  }
});

/**
 * Returns the CodeMirror extensions which show the coverage which is set by
 * the setLineCoverage effect: the line coverage, the branch and MC/DC
 * coverage of the lines and the uncovered regions.
 */
export function lineCoverage() {
  return [ lineCoverageField, coverageGutter, branchGutter, coverageTheme ];
}
