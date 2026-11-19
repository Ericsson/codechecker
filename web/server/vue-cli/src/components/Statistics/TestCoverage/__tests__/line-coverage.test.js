import { EditorState } from "@codemirror/state";

import {
  BRANCH_FULL,
  BRANCH_NONE,
  BRANCH_PARTIAL,
  COVERED,
  UNCOVERED,
  branchLevel,
  getBranchStatuses,
  getBranchTitle,
  getLineStatuses,
  getRegionRanges,
  lineCoverageField,
  setLineCoverage
} from "@/components/Statistics/TestCoverage/line-coverage";

function decoratedLines(state) {
  const lines = [];
  const decorations = state.field(lineCoverageField).decorations;
  decorations.between(0, state.doc.length, (from, to, decoration) => {
    lines.push([ state.doc.lineAt(from).number, decoration.spec.class ]);
  });
  return lines;
}

describe("Line coverage CodeMirror extension", () => {
  test("line statuses: covered wins", () => {
    const statuses = getLineStatuses({
      coveredLines: [ 1, 3 ],
      uncoveredLines: [ 2, 3 ]
    });

    expect([ ...statuses.entries() ].sort()).toEqual([
      [ 1, COVERED ], [ 2, UNCOVERED ], [ 3, COVERED ]
    ]);
    expect(getLineStatuses({}).size).toBe(0);
  });

  test("decorations follow the coverage effect", () => {
    let state = EditorState.create({
      doc: "a\nb\nc\nd",
      extensions: [ lineCoverageField ]
    });
    expect(decoratedLines(state)).toEqual([]);

    // Lines outside of the document are ignored.
    state = state.update({
      effects: setLineCoverage.of({
        coveredLines: [ 4, 1 ],
        uncoveredLines: [ 2, 99, 0 ]
      })
    }).state;

    expect(decoratedLines(state)).toEqual([
      [ 1, "cc-coverage-line-covered" ],
      [ 2, "cc-coverage-line-uncovered" ],
      [ 4, "cc-coverage-line-covered" ]
    ]);
    expect(state.field(lineCoverageField).statuses.get(2)).toBe(UNCOVERED);
  });

  test("content and coverage set in one transaction", () => {
    let state = EditorState.create({ extensions: [ lineCoverageField ] });

    state = state.update({
      changes: { from: 0, insert: "x\nyy\nz" },
      effects: setLineCoverage.of({
        coveredLines: [ 3 ],
        uncoveredRegions: [
          { startLine: 2, startCol: 1, endLine: 2, endCol: 3 }
        ]
      })
    }).state;

    expect(decoratedLines(state)).toEqual([
      [ 3, "cc-coverage-line-covered" ]
    ]);

    const marks = [];
    state.field(lineCoverageField).regionDecorations.between(
      0, state.doc.length, (from, to, deco) => {
        marks.push([ state.sliceDoc(from, to), deco.spec.class ]);
      });
    expect(marks).toEqual([ [ "yy", "cc-coverage-region-uncovered" ] ]);
  });

  test("branch levels", () => {
    expect(branchLevel(4, 4)).toBe(BRANCH_FULL);
    expect(branchLevel(3, 4)).toBe(BRANCH_PARTIAL);
    expect(branchLevel(0, 4)).toBe(BRANCH_NONE);
  });

  test("branch and MC/DC statuses of the lines", () => {
    const statuses = getBranchStatuses({
      lineBranches: [
        { line: 5, hit: 3, found: 4 },
        { line: 14, hit: 2, found: 2 },
        { line: 16, hit: 0, found: 2 },
        { line: 18, hit: 2, found: 4 },
        { line: 19, hit: 0, found: 2 }
      ],
      lineMcdc: [
        { line: 5, hit: 1, found: 2, uncoveredConditions: [ "C1" ] },
        { line: 14, hit: 1, found: 2, uncoveredConditions: [ "C2" ] },
        { line: 18, hit: 0, found: 2, uncoveredConditions: [ "C1", "C2" ] },
        { line: 19, hit: 0, found: 2, uncoveredConditions: [ "C1", "C2" ] },
        { line: 20, hit: 2, found: 2, uncoveredConditions: [] },
        { line: 21, hit: 0, found: 0 }
      ]
    });

    expect([ ...statuses.keys() ].sort((a, b) => a - b))
      .toEqual([ 5, 14, 16, 18, 19, 20 ]);
    expect(statuses.get(5)).toEqual({
      branchHit: 3, branchFound: 4, mcdcHit: 1, mcdcFound: 2,
      uncoveredConditions: [ "C1" ], level: BRANCH_PARTIAL
    });
    // Full only if both the branches and the conditions are fully covered,
    // none only if nothing is covered.
    expect(statuses.get(14).level).toBe(BRANCH_PARTIAL);
    expect(statuses.get(16).level).toBe(BRANCH_NONE);
    expect(statuses.get(18).level).toBe(BRANCH_PARTIAL);
    expect(statuses.get(19).level).toBe(BRANCH_NONE);
    expect(statuses.get(20).level).toBe(BRANCH_FULL);

    expect(getBranchTitle(statuses.get(5))).toBe(
      "Branches: 3 / 4 taken\n" +
      "MC/DC: 1 / 2 conditions covered\n" +
      "Uncovered conditions: C1");
    expect(getBranchTitle(statuses.get(16))).toBe("Branches: 0 / 2 taken");

    expect(getBranchStatuses({}).size).toBe(0);
  });

  test("uncovered region ranges", () => {
    const state = EditorState.create({ doc: "abcdef\nghij\nkl" });

    expect(getRegionRanges([
      // Multi-line region, the end column is exclusive.
      { startLine: 1, startCol: 3, endLine: 2, endCol: 3 },
      { startLine: 1, startCol: 1, endLine: 1, endCol: 2 },
      // Columns after the end of the line are clamped.
      { startLine: 3, startCol: 1, endLine: 3, endCol: 99 },
      // Empty and out of document regions are skipped.
      { startLine: 2, startCol: 2, endLine: 2, endCol: 2 },
      { startLine: 4, startCol: 1, endLine: 5, endCol: 1 }
    ], state.doc)).toEqual([
      { from: 0, to: 1 }, { from: 2, to: 9 }, { from: 12, to: 14 }
    ]);
    expect(getRegionRanges(null, state.doc)).toEqual([]);

    // Nested and overlapping regions are merged.
    expect(getRegionRanges([
      { startLine: 1, startCol: 1, endLine: 2, endCol: 5 },
      { startLine: 1, startCol: 3, endLine: 1, endCol: 5 },
      { startLine: 2, startCol: 3, endLine: 3, endCol: 2 },
      { startLine: 3, startCol: 2, endLine: 3, endCol: 3 }
    ], state.doc)).toEqual([ { from: 0, to: 14 } ]);
  });

  test("region decorations follow the coverage effect", () => {
    let state = EditorState.create({
      doc: "int f() {\n  return 0;\n}",
      extensions: [ lineCoverageField ]
    });

    state = state.update({
      effects: setLineCoverage.of({
        coveredLines: [ 1 ],
        uncoveredLines: [ 2 ],
        lineBranches: [ { line: 1, hit: 1, found: 2 } ],
        uncoveredRegions: [
          { startLine: 2, startCol: 3, endLine: 2, endCol: 12 }
        ]
      })
    }).state;

    const field = state.field(lineCoverageField);
    const marks = [];
    field.regionDecorations.between(0, state.doc.length, (from, to, deco) => {
      marks.push([ state.sliceDoc(from, to), deco.spec.class ]);
    });
    expect(marks).toEqual([ [ "return 0;", "cc-coverage-region-uncovered" ] ]);
    expect(field.branches.get(1).level).toBe(BRANCH_PARTIAL);
  });

  test("many lines", () => {
    const lineCount = 20000;
    const doc = Array.from({ length: lineCount }, (_, i) => `line ${i}`)
      .join("\n");
    const coveredLines = [];
    const uncoveredLines = [];
    for (let i = 1; i <= lineCount; ++i)
      (i % 3 ? coveredLines : uncoveredLines).push(i);

    const start = Date.now();
    const state = EditorState.create({
      doc,
      extensions: [ lineCoverageField ]
    }).update({
      effects: setLineCoverage.of({ coveredLines, uncoveredLines })
    }).state;

    expect(decoratedLines(state).length).toBe(lineCount);
    expect(Date.now() - start).toBeLessThan(2000);
  });
});
