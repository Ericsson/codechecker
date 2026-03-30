<template>
  <v-container
    ref="rootEl"
    fluid
    class="pa-0"
  >
    <v-row
      class="ma-0"
    >
      <v-col
        class="py-0"
        :cols="editorCols"
      >
        <v-container
          fluid
          class="pa-0 mb-2"
        >
          <v-row
            class="ma-0"
          >
            <v-col
              cols="auto"
              class="pa-0 mr-2"
              align-self="center"
            >
              <show-report-info-dialog :value="report" />
            </v-col>

            <v-col
              cols="auto"
              class="pa-0 mr-2"
              align-self="center"
            >
              <analysis-info-dialog
                :report-id="report?.reportId"
              />
            </v-col>

            <v-col
              cols="auto"
              class="pa-0 mr-2"
              align-self="center"
            >
              <set-cleanup-plan-btn
                :value="report ? [report] : []"
              />
            </v-col>

            <v-col
              cols="auto"
              class="review-status-wrapper pa-0 mr-2"
              align-self="center"
            >
              <v-container
                fluid
                class="pa-0"
              >
                <v-row>
                  <v-col
                    cols="auto"
                    class="pa-0"
                  >
                    <select-review-status
                      class="mx-0"
                      :value="reviewData"
                      :report="report"
                      :on-confirm="confirmReviewStatusChange"
                    />
                  </v-col>

                  <v-col cols="auto" class="pa-0">
                    <v-menu
                      v-if="reviewData.comment"
                      content-class="review-status-message-dialog"
                      :close-on-content-click="false"
                      :nudge-width="200"
                      offset-x
                    >
                      <template v-slot:activator="{ props: activatorProps }">
                        <v-btn
                          v-bind="activatorProps"
                          class="review-status-message"
                          icon="mdi-message-text-outline"
                          variant="text"
                        />
                      </template>
                      <v-card>
                        <v-list>
                          <v-list-item>
                            <template v-slot:prepend>
                              <user-icon :value="reviewData.author" />
                            </template>
                            <v-list-item-title>
                              {{ reviewData.author }}
                            </v-list-item-title>
                            <v-list-item-subtitle>
                              {{ prettifyDate(reviewData.date) }}
                            </v-list-item-subtitle>
                          </v-list-item>
                        </v-list>

                        <v-divider />

                        <v-list>
                          <v-list-item>
                            <v-list-item-title>
                              {{ reviewData.comment }}
                            </v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-card>
                    </v-menu>
                  </v-col>
                </v-row>
              </v-container>
            </v-col>

            <v-col
              cols="auto"
              class="pa-0"
              align-self="center"
            >
              <v-checkbox
                v-model="showArrows"
                class="show-arrows mx-2 my-0 align-center justify-center"
                label="Show arrows"
                density="compact"
                hide-details
              />
            </v-col>

            <v-spacer />

            <v-col
              cols="auto"
              class="py-0 pr-0"
              align-self="center"
            >
              <toggle-blame-view-btn
                v-model="enableBlameView"
                :disabled="!hasBlameInfo || loading"
              />
            </v-col>

            <v-col
              cols="auto"
              class="py-0 pr-0"
              align-self="center"
            >
              <v-btn
                class="comments-btn mx-2 mr-0"
                color="primary"
                variant="outlined"
                size="small"
                :loading="loadNumOfComments"
                @click="showComments = !showComments"
              >
                <v-icon
                  class="mr-1"
                  size="small"
                >
                  mdi-comment-multiple-outline
                </v-icon>
                Comments ({{ numOfComments }})
              </v-btn>
            </v-col>
          </v-row>
        </v-container>

        <v-container
          fluid
          class="pa-0"
        >
          <v-row
            id="editor-wrapper"
            class="ma-0"
          >
            <v-progress-linear
              v-if="loading"
              indeterminate
              class="mb-0"
            />

            <v-col class="pa-0">
              <v-container fluid class="pa-0">
                <v-row
                  class="header pa-1 ma-0"
                  justify="space-between"
                >
                  <v-col
                    v-if="trackingBranch"
                    class="file-path py-0"
                    align-self="center"
                    cols="auto"
                  >
                    <span
                      v-if="sourceFile"
                      :title="`Tracking branch: ${trackingBranch}`"
                      class="text-grey text-darken-3"
                    >
                      <v-icon class="mr-0" small>mdi-source-branch</v-icon>
                      ({{ truncate(trackingBranch, 20) }})
                    </span>
                  </v-col>

                  <v-col
                    v-if="trackingBranch"
                    class="py-1 px-0"
                    cols="auto"
                  >
                    <v-divider
                      inset
                      vertical
                      :style="{ display: 'inline' }"
                    />
                  </v-col>

                  <v-col
                    class="file-path py-0 pl-1"
                    align-self="center"
                  >
                    <copy-btn v-if="sourceFile" :value="sourceFile.filePath" />
                    <span
                      v-if="sourceFile"
                      class="file-path"
                      :title="`\u200E${sourceFile.filePath}`"
                    >
                      {{ sourceFile.filePath }}
                    </span>
                  </v-col>

                  <v-col
                    cols="auto"
                    class="py-0"
                    align-self="center"
                  >
                    <v-row
                      align="center"
                      class="text-no-wrap"
                    >
                      Found in:
                      <select-same-report
                        class="select-same-report ml-2"
                        :report="report"
                        @update:report="reportId =>
                          emit('update:report', reportId)"
                      />
                    </v-row>
                  </v-col>
                </v-row>

                <v-row
                  v-fill-height
                  :class="[
                    'editor',
                    'ma-0',
                    enableBlameView ? 'blame' : undefined
                  ]"
                >
                  <div ref="editorContainer" class="editor-container" />
                </v-row>
              </v-container>
            </v-col>
          </v-row>
        </v-container>
      </v-col>
      <v-col
        v-if="showComments"
        class="pa-0"
        :cols="commentCols"
      >
        <report-comments
          v-fill-height
          class="comments"
          :report="report"
          @update:comment-count="updateCommentCount"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import {
  computed,
  getCurrentInstance,
  h,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  render,
  watch
} from "vue";

import { useRoute } from "vue-router";

import {
  Decoration,
  EditorView,
  WidgetType,
  keymap,
  lineNumbers
} from "@codemirror/view";
import { findNext, openSearchPanel, searchKeymap } from "@codemirror/search";
import { EditorState, StateEffect, StateField } from "@codemirror/state";
import { cpp } from "@codemirror/lang-cpp";

import mitt from "mitt";

import { jsPlumb } from "jsplumb";

import { useDateUtils } from "@/composables/useDateUtils";
import { format } from "date-fns";

import { ccService, handleThriftError } from "@cc-api";
import {
  Checker,
  Encoding,
  ExtendedReportDataType,
  ReviewData
} from "@cc/report-server-types";

import { AnalysisInfoDialog, CopyBtn } from "@/components";
import { UserIcon } from "@/components/Icons";
import { FillHeight } from "@/directives";

import { SetCleanupPlanBtn } from "@/components/Report/CleanupPlan";
import ReportTreeKind from "@/components/Report/ReportTree/ReportTreeKind";

import { useGitBlame } from "@/composables/useGitBlame";
import { ReportComments } from "./Comment";
import ToggleBlameViewBtn from "./Git/ToggleBlameViewBtn";
import { ShowReportInfoDialog } from "./ReportInfo";
import SelectReviewStatus from "./SelectReviewStatus";
import SelectSameReport from "./SelectSameReport";

import ReportStepMessage from "./ReportStepMessage";

const props = defineProps({
  treeItem: { type: Object, default: null }
});

const emit = defineEmits([
  "update-review-data",
  "update:report"
]);

const route = useRoute();
const { prettifyDate } = useDateUtils();

const enableBlameView = ref(route.query["view"] === "blame");

const editorContainer = ref(null);
const report = ref(null);
const editor = ref(null);
const sourceFile = ref(null);
const jsPlumbInstance = ref(null);
const lineMarks = ref([]);
const showArrows = ref(true);
const numOfComments = ref(0);
const loadNumOfComments = ref(false);
const showComments = ref(false);
const commentCols = ref(3);
const loading = ref(true);
const bus = mitt();
const selectedChecker = ref(null);
const docUrl = ref(null);
const rootEl = ref(null);

const instance = getCurrentInstance();
const parentAppContext = instance.appContext;

const gitBlame = useGitBlame(editor, sourceFile);

const vFillHeight = FillHeight;

const addMarks = StateEffect.define();
const addWidgets = StateEffect.define();
const clearMarks = StateEffect.define();
const clearWidgets = StateEffect.define();

const markField = StateField.define({
  create() {
    return Decoration.none;
  },
  update(marks, tr) {
    marks = marks.map(tr.changes);

    for (const effect of tr.effects) {
      if (effect.is(clearMarks)) {
        return Decoration.none;
      }

      if (effect.is(addMarks)) {
        const decoration = effect.value.map(item => 
          Decoration.mark({
            class: "checker-step",
            attributes: { markerid: item.markerId }
          }).range(item.from, item.to)
        );
        return marks.update({ add: decoration });
      }
    }

    return marks;
  },
  provide: f => EditorView.decorations.from(f)
});

const lineWidgetField = context => {
  return StateField.define({
    create() {
      return Decoration.none;
    },
    update(widgets, tr) {
      widgets = widgets.map(tr.changes);

      for (const effect of tr.effects) {
        if (effect.is(clearWidgets)) {
          return Decoration.none;
        }

        if (effect.is(addWidgets)) {
          const decoration = effect.value.map(item =>
            Decoration.widget({
              widget: new AdvancedLineWidget(item.data, context),
              block: true,
              key: item.data.id
            }).range(item.pos)
          );
          return widgets.update({ add: decoration });
        }
      }

      return widgets;
    },
    provide: f => EditorView.decorations.from(f)
  });
};

const trackingBranch = computed(() => sourceFile.value?.trackingBranch);
const hasBlameInfo = computed(() => sourceFile.value?.hasBlameInfo);
const editorCols = computed(() => {
  const maxCols = 12;
  return showComments.value ? maxCols - commentCols.value : maxCols;
});
const reviewData = computed(() =>
  report.value?.reviewData || new ReviewData()
);

watch(enableBlameView, async () => {
  if (enableBlameView.value) {
    await gitBlame.loadBlameView();
  } else {
    await gitBlame.hideBlameView();
  }

  clearArrowLines();
  await nextTick();
  addArrowLines();

  jumpTo(
    props.treeItem.step?.startLine.toNumber() ||
      props.treeItem.report.line.toNumber(),
    0
  );
});

watch(() => props.treeItem, newTreeItem => {
  if (newTreeItem) {
    init(newTreeItem);
  }
}, { immediate: true });

watch(showArrows, async () => {
  await nextTick();
  if (showArrows.value) {
    await drawBugPath();
    addArrowLines();
  } else {
    clearHighlightWidgets();
    clearArrowLines();
  }
});

watch(report, () => {
  updateCommentCount(report.value);
});

class AdvancedLineWidget extends WidgetType {
  constructor(data, appContext) {
    super();
    this.data = data;
    this.appContext = appContext;
    this.container = null;
  }

  eq(other) {
    return other instanceof AdvancedLineWidget &&
      this.data.type === other.data.type &&
      this.data.index === other.data.index &&
      this.data.id === other.data.id;
  }
  
  toDOM() {
    this.container = document.createElement("div");
    const vnode = h(ReportStepMessage, this.data);
    vnode.appContext = this.appContext;

    render(vnode, this.container);

    return this.container;
  }

  destroy() {
    if (this.container) {
      render(null, this.container);
      this.container = null;
    }
  }

  ignoreEvent() {
    return false;
  }
}

onMounted(() => {
  document.addEventListener("keydown", findText);

  editor.value = new EditorView({
    parent: editorContainer.value,
    extensions: [
      lineNumbers(),
      EditorState.readOnly.of(true),
      cpp(),
      keymap.of(searchKeymap),
      EditorView.updateListener.of(update => {
        if (update.viewportChanged) {
          const viewport = update.view.viewport;
          highlightRange(viewport.from, viewport.to);
        }
      }),
      markField,
      lineWidgetField(parentAppContext),
      gitBlame.blameCompartment.of([])
    ]
  });

  if (props.treeItem) {
    init(props.treeItem);
  }

  bus.on("jpmToPrevReport", attrs => {
    loadReportStep(report.value, {
      stepId: attrs.$id,
      fileId: attrs.fileId,
      startLine: attrs.startLine
    });
  });

  bus.on("jpmToNextReport", attrs => {
    loadReportStep(report.value, {
      stepId: attrs.$id,
      fileId: attrs.fileId,
      startLine: attrs.startLine
    });
  });

  bus.on("showDocumentation", () => {
    selectedChecker.value = new Checker({
      analyzerName: report.value.analyzerName,
      checkerId: report.value.checkerId
    });
  });
});

onUnmounted(() => {
  document.removeEventListener("keydown", findText);
});

function init(_treeItem) {
  loading.value = true;

  if (_treeItem.step) {
    loadReportStep(_treeItem.report, {
      stepId: props.treeItem.id,
      ..._treeItem.step
    });
  } else if (_treeItem.data) {
    loadReportStep(_treeItem.report, {
      stepId: props.treeItem.id,
      ..._treeItem.data
    });
  } else {
    loadReport(_treeItem.report);
  }
}

function updateCommentCount(report) {
  loadNumOfComments.value = true;
  ccService.getClient().getCommentCount(
    report.reportId,
    handleThriftError(count => {
      numOfComments.value = count;
      loadNumOfComments.value = false;
    }));
}

async function loadReportStep(_report, { stepId, fileId, startLine }) {
  if (!report.value ||
      !report.value.reportId.equals(_report.reportId) ||
      !sourceFile.value ||
      !fileId.equals(sourceFile.value.fileId)
  ) {
    report.value = _report;

    await setSourceFileData(fileId);
    await drawBugPath();
  }

  const _line = startLine.toNumber();
  jumpTo(_line, 0);
  highlightReportStep(stepId);

  loading.value = false;
}

async function loadReport(_report) {
  if (!_report)
    return;

  report.value = _report;

  await setSourceFileData(_report.fileId);
  await drawBugPath();

  const _line = _report.line.toNumber();
  jumpTo(_line, 0);
  highlightReport(_report);

  loading.value = false;
}

function findText(evt) {
  if (evt.ctrlKey && evt.keyCode === 13) // Ctrl + Enter
    findNext(editor.value);

  if (evt.ctrlKey && evt.keyCode === 70) { // Ctrl + f
    evt.preventDefault();
    evt.stopPropagation();
    openSearchPanel(editor.value);

    // Set focus to the search input field.
    setTimeout(() => {
      const _searchField = document.querySelector(".cm-search input");
      if (_searchField) _searchField.focus();
    }, 0);
  }
}

function highlightReportStep(stepId) {
  highlightCurrentBubble(stepId);
}

function highlightReport() {
  document.querySelectorAll(".report-step-msg").forEach(node => {
    const _type = node.getAttribute("type");
    node.classList.toggle("current", _type === "error");
  });
}

function highlightCurrentBubble(id) {
  document.querySelectorAll(".report-step-msg").forEach(node => {
    const _stepId = node.getAttribute("step-id");
    node.classList.toggle("current", _stepId === id);
  });
}

async function setSourceFileData(fileId) {
  const _sourceFile = await new Promise(resolve => {
    ccService.getClient().getSourceFileData(fileId, true,
      Encoding.DEFAULT, handleThriftError(_sourceFile => {
        resolve(_sourceFile);
      }));
  });

  sourceFile.value = _sourceFile;
  editor.value.dispatch({
    changes: {
      from: 0,
      to: editor.value.state.doc.length,
      insert: _sourceFile.fileContent,
    }
  });

  if (enableBlameView.value) {
    gitBlame.loadBlameView();
  }
}

function resetJsPlumb() {
  if (jsPlumbInstance.value) {
    jsPlumbInstance.value.reset();
  }

  if (!rootEl.value) return;

  const _jsPlumbParentElement = editorContainer.value;
  _jsPlumbParentElement.style.position = "relative";

  jsPlumbInstance.value = jsPlumb.getInstance({
    Container : _jsPlumbParentElement,
    Anchor : [ "Perimeter", { shape : "Ellipse" } ],
    Endpoint : [ "Dot", { radius: 1 } ],
    PaintStyle : { stroke : "#a94442", strokeWidth: 2 },
    Connector: [ "Bezier", { curviness: 10 } ],
    ConnectionsDetachable : false,
    ConnectionOverlays : [
      [ "Arrow", { location: 1, length: 10, width: 8 } ]
    ]
  });
}

async function drawBugPath() {
  clearLineWidgets();
  clearHighlightWidgets();
  clearArrowLines();

  const _reportId = report.value.reportId;
  const _reportDetail = await new Promise(resolve => {
    ccService.getClient().getReportDetails(_reportId,
      handleThriftError(_reportDetail => {
        resolve(_reportDetail);
      }));
  });

  const _errorChecker = new Checker({
    analyzerName: report.value.analyzerName,
    checkerId: report.value.checkerId
  });
  await new Promise(resolve => {
    ccService.getClient().getCheckerLabels(
      [ _errorChecker ],
      handleThriftError(labels => {
        const _docUrlLabels = labels[0].filter(
          param => param.startsWith("doc_url")
        );
        docUrl.value = _docUrlLabels.length ?
          _docUrlLabels[0].split("doc_url:")[1] : null;
        resolve(docUrl.value);
      })
    );
  });

  const _isSameFile = path => path.fileId.equals(sourceFile.value.fileId);

  // Add extra path events (macro expansions, notes).
  const _extendedData = _reportDetail.extendedData.map((data, index) => {
    let kind = null;
    switch (data.type) {
    case ExtendedReportDataType.NOTE:
      kind = ReportTreeKind.NOTE_ITEM;
      break;
    case ExtendedReportDataType.MACRO:
      kind = ReportTreeKind.MACRO_EXPANSION_ITEM;
      break;
    default:
      console.warn("Unhandled extended data type", data.type);
    }

    const _id = ReportTreeKind.getId(kind, report.value, index);
    return { ...data, $id: _id, $message: data.message };
  }).filter(_isSameFile);

  addExtendedData(_extendedData);

  // Add file path events.
  let _prevStep = null;
  const _events = _reportDetail.pathEvents.map((event, index) => {
    const _id = ReportTreeKind.getId(ReportTreeKind.REPORT_STEPS,
      report.value, index);

    const _currentStep = {
      ...event,
      $id: _id,
      $message: event.msg,
      $index: index + 1,
      $isResult: index === _reportDetail.pathEvents.length - 1,
      $prevStep: _prevStep
    };

    if (_prevStep) {
      _prevStep.$nextStep = _currentStep;
    }
    _prevStep = _currentStep;

    return _currentStep;
  }).filter(_isSameFile);

  addEvents(_events);

  // Add lines.
  if (showArrows.value) {
    const _points = _reportDetail.executionPath.filter(_isSameFile);
    createArrowConnection(_points);
  }
}

function clearLineWidgets() {
  editor.value.dispatch({
    effects: clearWidgets.of(null)
  });
}

function addArrowLines() {
  const viewport = editor.value.viewport;
  highlightRange(viewport.from, viewport.to);
}

function clearHighlightWidgets() {
  lineMarks.value = [];
  editor.value.dispatch({
    effects: clearMarks.of(null)
  });
}

function clearArrowLines() {
  if (jsPlumbInstance.value) {
    jsPlumbInstance.value.reset();
  }
}

function createLineWidget(pos, data) {
  editor.value.dispatch({
    effects: addWidgets.of([
      { pos: pos, data: data }
    ])
  });
}

function createHighlightWidget(markerId, from, to) {
  editor.value.dispatch({
    effects: addMarks.of([
      { markerId: markerId, from: from, to: to }
    ])
  });
}

function addLineWidget(element, props) {
  const charWidth = 7.2;
  const marginLeft = charWidth * (element.startCol || 0) + "px";

  const line = editor.value.state.doc.line(element.startLine.toNumber());
  createLineWidget(
    line.to,
    {
      ...props,
      id: element.$id,
      value: element.$message,
      marginLeft: marginLeft,
      report: report.value
    }
  );
}

function renderMainWarning(events) {
  if (!sourceFile.value.fileId.equals(report.value.fileId)) {
    return false;
  }

  if (events.length == 0) {
    return true;
  }

  const _lastEvent = events[events.length - 1];
  if (report.value.checkerMsg !== _lastEvent.msg ||
    report.value.line.toNumber() != _lastEvent.startLine.toNumber()) {
    return true;
  }

  return false;
}

function addEvents(events) {
  events.forEach(event => {
    let _type = "info";
    if (event.$isResult) {
      _type = renderMainWarning(events) ? "info" : "error";
    } else if (event.msg.indexOf(" (fixit)") > -1) {
      _type = "fixit";
    }

    const _props = {
      type: _type,
      index: event.$index,
      bus: bus,
      prevStep: event.$prevStep,
      nextStep: event.$nextStep,
      docUrl: docUrl.value
    };
    addLineWidget(event, _props);
  });


  //If the warning message or location is different than the
  //the last bug path element, then we render the warning.
  if (renderMainWarning(events)) {
    const chkrmsg_data = { $id: 999,
      $message:report.value.checkerMsg,
      startLine:report.value.line, startCol:report.value.column };
    const chrkmsg_props = { type: "error", index:"E", hideDocUrl:true };
    addLineWidget(chkrmsg_data, chrkmsg_props);
  }

}

function addExtendedData(extendedData) {
  extendedData.forEach(data => {
    let _type = null;
    let _value = null;
    switch (data.type) {
    case ExtendedReportDataType.NOTE:
      _type = "note";
      _value = "Note";
      break;
    case ExtendedReportDataType.MACRO:
      _type = "macro";
      _value = "Macro Expansion";
      break;
    default:
      console.warn("Unhandled extended data type", data.type);
    }

    const _props = { type: _type, index: _value };
    addLineWidget(data, _props);
  });
}

function createArrowConnection(points) {
  points.forEach(p => {
    const fromLine = p.startLine - 1;
    const toLine = p.endLine - 1;
    const fromPos =
      editor.value.state.doc.line(fromLine + 1).from + p.startCol - 1;
    const toPos =
      editor.value.state.doc.line(toLine + 1).from + p.endCol.toNumber();
    const markerId =
      [ fromLine, p.startCol - 1, toLine, p.endCol.toNumber() ].join("_");

    createHighlightWidget(markerId, fromPos, toPos);

    lineMarks.value.push({
      markerId: markerId,
      from: fromPos,
      to: toPos
    });
  });
}

function highlightRange(_from, _to) {
  if (!lineMarks.value.length) {
    return;
  }

  resetJsPlumb();

  let _prev = null;
  lineMarks.value
    .filter(mark => mark.from >= _from && mark.to <= _to)
    .forEach(mark => {
      const _current = document.querySelector(`[markerid='${mark.markerId}']`);

      if (!_current) {
        return;
      }

      if (_prev) {
        jsPlumbInstance.value.connect({
          source : _prev,
          target : _current
        });
      }

      _prev = _current;
    });
}

function jumpTo(line, column) {
  const position = editor.value.state.doc.line(line).from + column;
  editor.value.dispatch({
    selection: { anchor: position },
    effects: EditorView.scrollIntoView(position, { y: "center" })
  });
}

function confirmReviewStatusChange(comment, status, author) {
  ccService.getClient().addReviewStatusRule(report.value.bugHash,
    status, comment, handleThriftError(() => {
      reviewData.value.comment = comment;
      reviewData.value.status = status;
      reviewData.value.author = author;
      reviewData.value.date = format(new Date(), "yyyy-MM-dd HH:mm:ss");
      emit(
        "update-review-data",
        reviewData.value,
        report.value.reportId
      );
    }));
}

function truncate(text, length) {
  if (!text) return "";
  if (text.length <= length) return text;
  return text.substring(0, length) + "...";
}
</script>

<style lang="scss">
#editor {
  width: 100%;
  height: 100%;
}

#editor-wrapper {
  border: 1px solid #d8dbe0;

  .header {
    background-color: #f7f7f7;

    .file-path {
      font-family: monospace;
      color: rgb(var(--v-theme-on-surface));

      max-width: 100%;
      display: inline-block;
      text-align: left;
      vertical-align: middle;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      direction: rtl;

      &::before {
        content: '\200e';
      }
    }
  }

  .editor {
    font-size: initial;
    line-height: initial;

    :deep(.cm-line:hover) {
      background-color: #f5f5f5;
    }

    &.blame :deep(.cm-editor) {
      line-height: 21px;

      .CodeMirror-gutter-wrapper {
        &, div, span {
          height: 100%;
        }
      }
    }

    :deep(.cm-searchMatch) {
      background-color: lightgreen;
    }

    :deep(.cm-searchMatch-selected) {
      background-color: green;
    }
  }
}

.checker-step {
  background-color: #eeb;
}

.blame-gutter {
  width: 400px;
  background-color: #f7f7f7;
}
</style>