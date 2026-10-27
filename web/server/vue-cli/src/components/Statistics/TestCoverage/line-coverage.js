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

/**
 * Effect which sets the line coverage of the document. Its value is an
 * object with "coveredLines" and "uncoveredLines" arrays of 1-based line
 * numbers.
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
    return { statuses: new Map(), decorations: Decoration.none };
  },
  update(value, tr) {
    for (const effect of tr.effects) {
      if (effect.is(setLineCoverage)) {
        const statuses = getLineStatuses(effect.value || {});
        return {
          statuses,
          decorations: buildDecorations(statuses, tr.state.doc)
        };
      }
    }

    if (tr.docChanged) {
      return { ...value, decorations: value.decorations.map(tr.changes) };
    }

    return value;
  },
  provide: field =>
    EditorView.decorations.from(field, value => value.decorations)
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
  }
});

/**
 * Returns the CodeMirror extensions which show the line coverage which is
 * set by the setLineCoverage effect.
 */
export function lineCoverage() {
  return [ lineCoverageField, coverageGutter, coverageTheme ];
}
