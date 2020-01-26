<template>
  <v-container fluid>
    <v-row class="mb-2 mx-0">
      <v-col
        cols="auto"
        class="pa-0 mr-2"
        align-self="center"
      >
        <v-btn color="primary" outlined>
          <v-icon>mdi-file-document-box-outline</v-icon>
          Show documentation
        </v-btn>
      </v-col>

      <v-col
        cols="auto"
        class="pa-0 mr-2"
        align-self="center"
      >
        <select-review-status
          class="mx-0"
          :value="reviewStatus"
        />
      </v-col>

      <v-col
        cols="auto"
        class="pa-0"
        align-self="center"
      >
        <v-checkbox
          class="mx-2 my-0 align-center justify-center"
          label="Show arrows"
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
        >
          <v-icon>mdi-comment-multiple-outline</v-icon>
          Comments (0)
        </v-btn>
      </v-col>
    </v-row>

    <v-row
      id="editor-wrapper"
      class="mx-0"
    >
      <v-col class="pa-0">
        <v-row
          class="header pa-2 mx-0"
        >
          <v-col
            cols="auto"
            class="py-0"
            align-self="center"
          >
            <span
              v-if="sourceFile"
              class="file-path"
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
            <v-row align="center">
              Also found in:
              <select-same-report
                class="ml-2"
                :report="report"
              />
            </v-row>
          </v-col>
        </v-row>

        <v-row
          v-fill-height
          class="mx-0"
        >
          <textarea ref="editor" />
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import Vue from 'vue';

import VContainer from "Vuetify/VGrid/VContainer";
import VSpacer from "Vuetify/VGrid/VSpacer";
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";
import VCheckbox from "Vuetify/VCheckbox/VCheckbox";
import VRow from "Vuetify/VGrid/VRow";
import VCol from "Vuetify/VGrid/VCol";

import CodeMirror from 'codemirror';
import { jsPlumb } from 'jsplumb';

import { ccService } from '@cc-api';
import { Encoding } from '@cc/report-server-types';

import { FillHeight } from "@/directives";
import ReportTreeKind from './ReportTree/ReportTreeKind';

import SelectReviewStatus from './SelectReviewStatus';
import SelectSameReport from './SelectSameReport';

import ReportStepMessage from './ReportStepMessage';
const ReportStepMessageClass = Vue.extend(ReportStepMessage)


export default {
  name: 'Report',
  components: {
    VContainer, VSpacer, VBtn, VIcon, VCheckbox, VRow, VCol,
    SelectReviewStatus,
    SelectSameReport
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
      reviewStatus: null,
      jsPlumbInstance: null,
      lineMarks: [],
      lineWidgets: []
    };
  },

  watch: {
    treeItem() {
      this.init(this.treeItem);
    }
  },

  mounted() {
    this.editor = CodeMirror.fromTextArea(this.$refs.editor, {
      lineNumbers: true,
      readOnly: true,
      mode: 'text/x-c++src',
      gutters: ['CodeMirror-linenumbers', 'bugInfo'],
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
      this.highlightReportStep(step);
    },

    async loadReport(report) {
      if (this.report && this.report.reportId.equals(report.reportId)) {
        this.highlightReport(report);
        return;
      }

      this.report = report;

      this.reviewStatus = report.reviewData.status;

      await this.setSourceFileData(report.fileId);
      await this.drawBugPath();

      this.jumpTo(report.line.toNumber(), 0);
      this.highlightReport(report);
    },

    highlightReportStep() {
      this.highlightCurrentBubble(this.treeItem.id);
    },

    highlightReport() {
      // TODO:
    },

    highlightCurrentBubble(id) {
      this.lineWidgets.forEach((widget) => {
        const stepId = widget.node.getAttribute("step-id");
        widget.node.classList.toggle("current", stepId === id);
      });
    },

    async setSourceFileData(fileId) {
      const sourceFile = await new Promise((resolve) => {
        ccService.getClient().getSourceFileData(fileId, true,
        Encoding.DEFAULT, (err, sourceFile) => {
          resolve(sourceFile);
        });
      });

      this.sourceFile = sourceFile;
      this.editor.setValue(sourceFile.fileContent);
    },

    resetJsPlumb() {
      const jsPlumbParentElement =
        this.$el.querySelector('.CodeMirror-lines');
      jsPlumbParentElement.style.position = 'relative';

      this.jsPlumbInstance = jsPlumb.getInstance({
        Container : jsPlumbParentElement,
        Anchor : ['Perimeter', { shape : 'Ellipse' }],
        Endpoint : ['Dot', { radius: 1 }],
        PaintStyle : { stroke : '#a94442', strokeWidth: 2 },
        Connector: ['Bezier', { curviness: 10 }],
        ConnectionsDetachable : false,
        ConnectionOverlays : [
          ['Arrow', { location: 1, length: 10, width: 8 }]
        ]
      });
    },

    async drawBugPath() {
      this.clearBubbles();
      this.clearLines();

      const reportId = this.report.reportId;

      const reportDetail = await new Promise((resolve) => {
        ccService.getClient().getReportDetails(reportId,
        (err, reportDetail) => {
          resolve(reportDetail);
        });
      });

      const points = reportDetail.executionPath.filter((path) => {
        return path.fileId.equals(this.sourceFile.fileId);
      });
      const bubbles = reportDetail.pathEvents.map((event, index) => {
        const id =
          `${reportId}_${ReportTreeKind.REPORT_STEPS}_${index}`;

        return { ...event, $id: id };
      }).filter((path) => {
        return path.fileId.equals(this.sourceFile.fileId);
      });

      this.addBubbles(bubbles);
      this.addLines(points);
    },

    clearBubbles() {
      this.lineWidgets.forEach(widget => widget.clear());
      this.lineWidgets = [];
    },

    clearLines() {
      this.lineMarks.forEach(mark => mark.clear());
      this.lineMarks = [];
      this.resetJsPlumb();
    },

    addBubbles(bubbles) {
      this.editor.operation(() => {
        bubbles.forEach((bubble, index) => {
          if (!bubble.fileId.equals(this.sourceFile.fileId)) return;

          var isResult = index === bubbles.length - 1;
          const type = isResult
            ? "error" : bubble.msg.indexOf(" (fixit)") > -1
            ? "fixit" : "info";

          const marginLeft =
            this.editor.defaultCharWidth() * bubble.startCol + 'px';

          const widget = new ReportStepMessageClass({
            propsData: {
              id: bubble.$id,
              value: bubble.msg,
              marginLeft: marginLeft,
              type: type,
              index: index + 1
            }
          });
          widget.$mount();

          this.lineWidgets.push(this.editor.addLineWidget(
            bubble.startLine.toNumber() - 1, widget.$el));
        });
      });
    },

    addLines(points) {
      this.editor.operation(() => {
        points.forEach((p) => {
          const from = { line : p.startLine - 1, ch : p.startCol - 1 };
          const to =   { line : p.endLine - 1,   ch : p.endCol.toNumber() };
          const markerId = [from.line, from.ch, to.line, to.ch].join('_');

          let opts = {
            className: 'checker-step',
            attributes: {
              markerid: markerId
            }
          };

          this.lineMarks.push(this.editor.getDoc().markText(from, to, opts));
        });
      });

      const range = this.editor.getViewport();
      this.drawLines(range.from, range.to);
    },

    drawLines(/*from, to*/) {
      if (!this.lineMarks.length) {
        return;
      }

      let prev = null;
      this.lineMarks.forEach((textMarker) => {
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
    }
  }
}
</script>

<style lang="scss">
#editor-wrapper {
  border: 1px solid #d8dbe0;

  >.header {
    background-color: var(--v-grey-lighten3);

    .file-path {
      font-family: monospace;
      color: var(--v-grey-darken4);
    }
  }
}

.checker-step {
  background-color: #eeb;
}

.report-step-msg.current {
  border: 2px dashed var(--v-primary-base) !important;
}
</style>