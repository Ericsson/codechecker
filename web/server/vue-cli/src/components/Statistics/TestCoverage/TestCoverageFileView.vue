<template>
  <div class="test-coverage-file-view w-100">
    <v-row class="ma-0 mb-2" align="center">
      <v-btn
        :to="backLink"
        prepend-icon="mdi-arrow-left"
        color="primary"
        variant="text"
        class="mr-2"
      >
        Back
      </v-btn>

      <span class="text-body-2 mr-4">
        <v-icon size="small" class="mr-1">
          mdi-format-list-numbered
        </v-icon>
        Lines: {{ formatCounts(lineCounts) }}
      </span>
      <span class="text-body-2 mr-4">
        <v-icon size="small" class="mr-1">
          mdi-function-variant
        </v-icon>
        Functions: {{ formatCounts(functionCounts) }}
      </span>

      <v-spacer />

      <div
        class="coverage-legend d-flex align-center text-body-2"
        aria-label="Legend"
      >
        <span class="legend-item legend-covered mr-3">
          <v-icon size="small" color="success">mdi-check</v-icon>
          Executed
        </span>
        <span class="legend-item legend-uncovered mr-3">
          <v-icon size="small" color="error">mdi-close</v-icon>
          Not executed
        </span>
        <span class="legend-item">
          No marker: not executable
        </span>
      </div>
    </v-row>

    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-2"
    >
      {{ error }}
    </v-alert>

    <v-alert
      v-else-if="!loading && noLineData"
      type="info"
      variant="tonal"
      class="mb-2"
    >
      There is no test coverage data for this file in this run.
    </v-alert>

    <div v-show="!error" class="editor-wrapper">
      <v-row class="header pa-1 ma-0 flex-nowrap" align="center">
        <copy-btn v-if="filePath" :value="filePath" />
        <span class="file-path text-body-2" :title="filePath">
          {{ filePath }}
        </span>
      </v-row>

      <v-progress-linear
        v-if="loading"
        indeterminate
      />

      <v-row v-fill-height class="editor ma-0">
        <div ref="editorContainer" class="editor-container" />
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { basicSetup } from "codemirror";
import { EditorView } from "@codemirror/view";
import { Compartment, EditorState } from "@codemirror/state";

import { ccService, handleThriftError } from "@cc-api";
import { Encoding } from "@cc/report-server-types";
import { CopyBtn } from "@/components";
import { FillHeight } from "@/directives";
import { getLanguageExtension } from "@/utilities/codemirror";

import { formatPercentage, percentage } from "./coverage-tree";
import { lineCoverage, setLineCoverage } from "./line-coverage";

const props = defineProps({
  runId: { type: Number, required: true },
  fileId: { type: Number, required: true },
  // Normalized FileCoverage summary of the file (if known).
  fileCoverage: { type: Object, default: null },
  // Route location of the directory view.
  backLink: { type: Object, required: true }
});

const vFillHeight = FillHeight;

const editorContainer = ref(null);
const editor = ref(null);
const loading = ref(false);
const error = ref(null);
const sourceFilePath = ref(null);
const lineData = ref(null);
const languageCompartment = new Compartment();

// Identifies the latest request so the result of an older one is ignored.
let requestId = 0;

const filePath = computed(() =>
  sourceFilePath.value || props.fileCoverage?.filePath || "");

const noLineData = computed(() => !!lineData.value &&
  !lineData.value.coveredLines.length &&
  !lineData.value.uncoveredLines.length);

const lineCounts = computed(() => {
  if (lineData.value) {
    const hit = lineData.value.coveredLines.length;
    return { hit, found: hit + lineData.value.uncoveredLines.length };
  }
  return props.fileCoverage ? {
    hit: props.fileCoverage.linesHit,
    found: props.fileCoverage.linesFound
  } : null;
});

const functionCounts = computed(() => props.fileCoverage ? {
  hit: props.fileCoverage.functionsHit,
  found: props.fileCoverage.functionsFound
} : null);

function formatCounts(counts) {
  if (!counts)
    return "-";

  return `${counts.hit} / ${counts.found} ` +
    `(${formatPercentage(percentage(counts.hit, counts.found))})`;
}

function getSourceFileData(fileId) {
  return new Promise((resolve, reject) => {
    ccService.getClient().getSourceFileData(fileId, true, Encoding.DEFAULT,
      handleThriftError(resolve, reject));
  });
}

function getFileLineCoverage(runId, fileId) {
  return new Promise((resolve, reject) => {
    ccService.getClient().getFileLineCoverage(runId, fileId,
      handleThriftError(resolve, reject));
  });
}

function toNumbers(lines) {
  return (lines || []).map(line =>
    typeof line?.toNumber === "function" ? line.toNumber() : Number(line));
}

async function load() {
  const currentRequest = ++requestId;
  loading.value = true;
  error.value = null;
  lineData.value = null;

  try {
    const [ sourceFile, lineCoverageData ] = await Promise.all([
      getSourceFileData(props.fileId),
      getFileLineCoverage(props.runId, props.fileId)
    ]);
    if (currentRequest !== requestId || !editor.value)
      return;

    // The server returns an empty object for unknown files.
    if (typeof sourceFile?.fileContent !== "string")
      throw new Error("the source file is not stored on the server.");

    sourceFilePath.value = sourceFile.filePath;
    lineData.value = {
      coveredLines: toNumbers(lineCoverageData.coveredLines),
      uncoveredLines: toNumbers(lineCoverageData.uncoveredLines)
    };

    editor.value.dispatch({
      changes: {
        from: 0,
        to: editor.value.state.doc.length,
        insert: sourceFile.fileContent
      },
      effects: [
        languageCompartment.reconfigure(
          getLanguageExtension(sourceFile.filePath)),
        setLineCoverage.of(lineData.value)
      ]
    });

    scrollToFirstUncoveredLine();
  } catch (err) {
    if (currentRequest !== requestId)
      return;

    sourceFilePath.value = null;
    error.value = "The source file or its test coverage could not be " +
      `loaded: ${err?.message || err}`;
  } finally {
    if (currentRequest === requestId)
      loading.value = false;
  }
}

function scrollToFirstUncoveredLine() {
  const doc = editor.value.state.doc;
  const firstLine = lineData.value.uncoveredLines.reduce(
    (min, line) => Math.min(min, line), Infinity);
  const line = firstLine <= doc.lines ? firstLine : 1;

  editor.value.dispatch({
    effects: EditorView.scrollIntoView(doc.line(line).from, { y: "center" })
  });
}

watch(() => [ props.runId, props.fileId ], load);

onMounted(() => {
  editor.value = new EditorView({
    parent: editorContainer.value,
    extensions: [
      basicSetup,
      EditorState.readOnly.of(true),
      languageCompartment.of([]),
      lineCoverage()
    ]
  });

  load();
});

onUnmounted(() => {
  ++requestId;
  editor.value?.destroy();
  editor.value = null;
});
</script>

<style lang="scss" scoped>
.editor-wrapper {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));

  .header {
    background-color: rgba(var(--v-theme-on-surface), 0.04);
  }

  .file-path {
    min-width: 0;
    font-family: monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .editor-container {
    width: 100%;
  }

  :deep(.cm-editor) {
    font-size: 12px;
  }
}
</style>
