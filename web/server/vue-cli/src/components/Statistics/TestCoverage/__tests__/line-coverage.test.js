import { EditorState } from "@codemirror/state";

import {
  COVERED,
  UNCOVERED,
  getLineStatuses,
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
      changes: { from: 0, insert: "x\ny\nz" },
      effects: setLineCoverage.of({ coveredLines: [ 3 ] })
    }).state;

    expect(decoratedLines(state)).toEqual([
      [ 3, "cc-coverage-line-covered" ]
    ]);
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
