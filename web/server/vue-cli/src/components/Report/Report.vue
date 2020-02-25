<template>
  <v-container fluid>
    <v-row>
      <v-col
        class="py-0"
        :cols="editorCols"
      >
        <v-row class="mb-2 mx-0">
          <v-col
            cols="auto"
            class="pa-0 mr-2"
            align-self="center"
          >
            <show-documentation-button
              :value="checkerId"
            />
          </v-col>

          <v-col
            cols="auto"
            class="pa-0"
            align-self="center"
          >
            <v-row class="px-4">
              <select-review-status
                class="mx-0"
                :value="reviewData"
                :on-confirm="confirmReviewStatusChange"
              />

              <v-menu
                v-if="reviewData.comment"
                :close-on-content-click="false"
                :nudge-width="200"
                offset-x
              >
                <template v-slot:activator="{ on }">
                  <v-btn icon v-on="on">
                    <v-icon>mdi-message-text-outline</v-icon>
                  </v-btn>
                </template>
                <v-card>
                  <v-list>
                    <v-list-item>
                      <v-list-item-avatar>
                        <user-icon :value="reviewData.author" />
                      </v-list-item-avatar>

                      <v-list-item-content>
                        <v-list-item-title>
                          {{ reviewData.author }}
                        </v-list-item-title>
                        <v-list-item-subtitle>
                          {{ reviewData.date }}
                        </v-list-item-subtitle>
                      </v-list-item-content>
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
            </v-row>
          </v-col>

          <v-col
            cols="auto"
            class="pa-0"
            align-self="center"
          >
            <v-checkbox
              v-model="showArrows"
              class="mx-2 my-0 align-center justify-center"
              label="Show arrows"
              dense
              :hide-details="true"
            />
          </v-col>

          <v-spacer />

          <v-col
            cols="auto"
            class="py-0 pr-0"
            align-self="center"
          >
            <v-btn
              class="mx-2 mr-0"
              color="primary"
              outlined
              small
              :loading="loadNumOfComments"
              @click="showComments = !showComments"
            >
              <v-icon
                class="mr-1"
                small
              >
                mdi-comment-multiple-outline
              </v-icon>
              Comments({{ numOfComments }})
            </v-btn>
          </v-col>
        </v-row>

        <v-row
          id="editor-wrapper"
          class="mx-0"
        >
          <v-col class="pa-0">
            <v-row
              class="header pa-1 mx-0"
            >
              <v-col
                cols="auto"
                class="file-path py-0"
                align-self="center"
              >
                <span
                  v-if="sourceFile"
                  :title="sourceFile.filePath"
                >
                  {{ sourceFile.filePath }}
                </span>
              </v-col>

              <v-spacer />

              <v-col
                cols="auto"
                class="py-0"
                align-self="center"
              >
                <v-row
                  align="center"
                  class="text-no-wrap"
                >
                  Also found in:
                  <select-same-report
                    class="ml-2"
                    :report="report"
                    @update:report="(reportId) =>
                      $emit('update:report', reportId)"
                  />
                </v-row>
              </v-col>
            </v-row>

            <v-row
              v-fill-height
              class="editor mx-0"
            >
              <textarea ref="editor" />
            </v-row>
          </v-col>
        </v-row>
      </v-col>
      <v-col
        v-if="showComments"
        class="pa-0"
        :cols="commentCols"
      >
        <report-comments
          v-fill-height
          :report="report"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import Vue from "vue";

import CodeMirror from "codemirror";
import { jsPlumb } from "jsplumb";

import { ccService } from "@cc-api";
import {
  Encoding,
  ExtendedReportDataType,
  ReviewData
} from "@cc/report-server-types";

import { FillHeight } from "@/directives";
import { UserIcon } from "@/components/Icons";

import ReportTreeKind from "@/components/Report/ReportTree/ReportTreeKind";

import { ReportComments } from "./Comment";
import SelectReviewStatus from "./SelectReviewStatus";
import SelectSameReport from "./SelectSameReport";
import ShowDocumentationButton from "./ShowDocumentationButton";

import ReportStepMessage from "./ReportStepMessage";
const ReportStepMessageClass = Vue.extend(ReportStepMessage)


export default {
  name: "Report",
  components: {
    ReportComments,
    SelectReviewStatus,
    SelectSameReport,
    ShowDocumentationButton,
    UserIcon
  },
  directives: { FillHeight },
  props: {
    treeItem: { type: Object, default: null }
  },
  data() {
    return {
      report: null,
      step: null,
      editor: null,
      sourceFile: null,
      reviewData: new ReviewData(),
      jsPlumbInstance: null,
      lineMarks: [],
      lineWidgets: [],
      showArrows: true,
      numOfComments: null,
      loadNumOfComments: true,
      showComments: false,
      commentCols: 3
    };
  },

  computed: {
    checkerId() {
      return this.report ? this.report.checkerId : null;
    },

    editorCols() {
      const maxCols = 12;

      return this.showComments
        ? maxCols - this.commentCols
        : maxCols;
    }
  },

  watch: {
    treeItem() {
      this.init(this.treeItem);
    },

    showArrows() {
      if (this.showArrows) {
        this.drawBugPath();
      } else {
        this.clearLines();
      }
    },

    report() {
      this.loadNumOfComments = true;
      ccService.getClient().getCommentCount(this.report.reportId,
      (err, numOfComments) => {
        this.numOfComments = numOfComments;
        this.loadNumOfComments = false;
      });
    }
  },

  mounted() {
    this.editor = CodeMirror.fromTextArea(this.$refs.editor, {
      lineNumbers: true,
      readOnly: true,
      mode: "text/x-c++src",
      gutters: [ "CodeMirror-linenumbers", "bugInfo" ],
      extraKeys: {},
      viewportMargin: 500
    });
    this.editor.setSize("100%", "100%");

    if (this.treeItem) {
      this.init(this.treeItem);
    }
  },

  methods: {
    init(treeItem) {
      if (treeItem.step) {
        this.loadReportStep(treeItem.report, treeItem.step);
      } else if (treeItem.data) {
        this.loadReportStep(treeItem.report, treeItem.data);
      } else {
        this.loadReport(treeItem.report);
      }
    },

    async loadReportStep(report, step) {
      this.step = step;

      if (!this.report ||
          !this.report.reportId.equals(report.reportId) ||
          !this.sourceFile ||
          !step.fileId.equals(this.sourceFile.fileId)
      ) {
        this.report = report;

        await this.setSourceFileData(step.fileId);
        await this.drawBugPath();
      }

      this.jumpTo(step.startLine.toNumber(), 0);
      this.highlightReportStep();
    },

    async loadReport(report) {
      if (this.report && this.report.reportId.equals(report.reportId)) {
        this.highlightReport(report);
        return;
      }

      this.report = report;

      this.reviewData = report.reviewData;

      await this.setSourceFileData(report.fileId);
      await this.drawBugPath();

      this.jumpTo(report.line.toNumber(), 0);
      this.highlightReport(report);
    },

    highlightReportStep() {
      this.highlightCurrentBubble(this.treeItem.id);
    },

    highlightReport() {
      this.lineWidgets.forEach(widget => {
        const type = widget.node.getAttribute("type");
        widget.node.classList.toggle("current", type === "error");
      });
    },

    highlightCurrentBubble(id) {
      this.lineWidgets.forEach(widget => {
        const stepId = widget.node.getAttribute("step-id");
        widget.node.classList.toggle("current", stepId === id);
      });
    },

    async setSourceFileData(fileId) {
      const sourceFile = await new Promise(resolve => {
        ccService.getClient().getSourceFileData(fileId, true,
        Encoding.DEFAULT, (err, sourceFile) => {
          resolve(sourceFile);
        });
      });

      this.sourceFile = sourceFile;
      this.editor.setValue(sourceFile.fileContent);
    },

    resetJsPlumb() {
      if (this.jsPlumbInstance) {
        this.jsPlumbInstance.reset();
      }

      const jsPlumbParentElement =
        this.$el.querySelector(".CodeMirror-lines");
      jsPlumbParentElement.style.position = "relative";

      this.jsPlumbInstance = jsPlumb.getInstance({
        Container : jsPlumbParentElement,
        Anchor : [ "Perimeter", { shape : "Ellipse" } ],
        Endpoint : [ "Dot", { radius: 1 } ],
        PaintStyle : { stroke : "#a94442", strokeWidth: 2 },
        Connector: [ "Bezier", { curviness: 10 } ],
        ConnectionsDetachable : false,
        ConnectionOverlays : [
          [ "Arrow", { location: 1, length: 10, width: 8 } ]
        ]
      });
    },

    isSameFile (filePath) {
      return filePath.fileId === this.sourceFile.fileId;
    },

    async drawBugPath() {
      this.clearBubbles();
      this.clearLines();

      const reportId = this.report.reportId;

      const reportDetail = await new Promise(resolve => {
        ccService.getClient().getReportDetails(reportId,
        (err, reportDetail) => {
          resolve(reportDetail);
        });
      });

      const isSameFile = path => path.fileId.equals(this.sourceFile.fileId);

      // Add extra path events (macro expansions, notes).
      const extendedData = reportDetail.extendedData.map((data, index) => {
        let kind = null;
        switch(data.type) {
          case ExtendedReportDataType.NOTE:
            kind = ReportTreeKind.NOTE_ITEM;
            break;
          case ExtendedReportDataType.MACRO:
            kind = ReportTreeKind.MACRO_EXPANSION_ITEM;
            break;
          default:
            console.warning("Unhandled extended data type", data.type);
        }

        const id = ReportTreeKind.getId(kind, this.report, index);
        return { ...data, $id: id, $message: data.message };
      }).filter(isSameFile);

      this.addExtendedData(extendedData);

      // Add file path events.
      const events = reportDetail.pathEvents.map((event, index) => {
        const id = ReportTreeKind.getId(ReportTreeKind.REPORT_STEPS,
          this.report, index);

        return {
          ...event,
          $id: id,
          $message: event.msg,
          $index: index + 1,
          $isResult: index === reportDetail.pathEvents.length - 1
        };
      }).filter(isSameFile);

      this.addEvents(events);

      // Add lines.
      if (this.showArrows) {
        const points = reportDetail.executionPath.filter(isSameFile);
        this.addLines(points);
      }
    },

    clearBubbles() {
      this.editor.operation(() => {
        this.lineWidgets.forEach(widget => widget.clear());
      });

      this.lineWidgets = [];
    },

    clearLines() {
      this.editor.operation(() => {
        this.lineMarks.forEach(mark => mark.clear());
      });

      this.lineMarks = [];
      this.resetJsPlumb();
    },

    addLineWidget(element, props) {
      const marginLeft =
        this.editor.defaultCharWidth() * element.startCol + "px";

      const widget = new ReportStepMessageClass({
        propsData: {
          ...props,
          id: element.$id,
          value: element.$message,
          marginLeft: marginLeft,
        }
      });
      widget.$mount();

      this.lineWidgets.push(this.editor.addLineWidget(
        element.startLine.toNumber() - 1, widget.$el));
    },

    addEvents(events) {
      this.editor.operation(() => {
        events.forEach(event => {
          const type = event.$isResult
            ? "error" : event.msg.indexOf(" (fixit)") > -1
            ? "fixit" : "info";

          const props = { type: type, index: event.$index };
          this.addLineWidget(event, props);
        });
      });
    },

    addExtendedData(extendedData) {
      this.editor.operation(() => {
        extendedData.forEach(data => {
          let type = null;
          let value = null;
          switch(data.type) {
            case ExtendedReportDataType.NOTE:
              type = "note";
              value = "Note";
              break;
            case ExtendedReportDataType.MACRO:
              type = "macro";
              value = "Macro Expansion";
              break;
            default:
              console.warning("Unhandled extended data type", data.type);
          }

          const props = { type: type, showArrows: false, index: value };
          this.addLineWidget(data, props);
        });
      });
    },

    addLines(points) {
      this.editor.operation(() => {
        points.forEach(p => {
          const from = { line : p.startLine - 1, ch : p.startCol - 1 };
          const to =   { line : p.endLine - 1,   ch : p.endCol.toNumber() };
          const markerId = [ from.line, from.ch, to.line, to.ch ].join("_");

          let opts = {
            className: "checker-step",
            attributes: {
              markerid: markerId
            }
          };

          this.lineMarks.push(this.editor.getDoc().markText(from, to, opts));
        });
      });

      const range = this.editor.getViewport();

      // Use setTimeout to make sure that the previously marked texts are
      // rendered.
      setTimeout(() => {
        this.drawLines(range.from, range.to);
      }, 0);
    },

    drawLines(/*from, to*/) {
      if (!this.lineMarks.length) {
        return;
      }

      let prev = null;
      this.lineMarks.forEach(textMarker => {
        const current = this.getDomToMarker(textMarker);

        if (!current) {
          return;
        }

        if (prev) {
          this.jsPlumbInstance.connect({
            source : prev,
            target : current
          });
        }

        prev = current;
      });
    },

    getDomToMarker(textMarker) {
      const selector = `[markerid='${textMarker.attributes.markerid}']`;
      return this.$el.querySelector(selector);
    },

    jumpTo(line, column) {
      this.editor.scrollIntoView({
        line: line,
        ch: column
      }, 150);
    },

    confirmReviewStatusChange(reviewData) {
      ccService.getClient().changeReviewStatus(this.report.reportId,
      reviewData.status, reviewData.comment, () => {
        // TODO: handle errors.
      });
    }
  }
}
</script>

<style lang="scss" scoped>
#editor-wrapper {
  border: 1px solid #d8dbe0;

  .header {
    background-color: "#f7f7f7";

    .file-path {
      font-family: monospace;
      color: var(--v-grey-darken4);

      max-width: 40%;
      display: inline-block;
      text-align: left;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      direction: rtl;
    }
  }

  .editor {
    font-size: initial;
    line-height: initial;
  }
}

::v-deep .checker-step {
  background-color: #eeb;
}

::v-deep .report-step-msg.current {
  border: 2px dashed var(--v-primary-base) !important;
}
</style>