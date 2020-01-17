<template>
  <v-container fluid>
    <v-card>
      <v-card-title>
        <v-btn class="mr-2" color="primary">
          <v-icon>mdi-file-document-box-outline</v-icon>
          Show documentation
        </v-btn>

        <select-review-status />

        <v-checkbox label="Show arrows" />

        <v-spacer />

        <v-btn>
          <v-icon>mdi-comment-multiple-outline</v-icon>
          Comments (0)
        </v-btn>
      </v-card-title>
      <v-card-subtitle>
        <v-toolbar dense flat>
          <v-toolbar-title>
            <span v-if="sourceFile">{{ sourceFile.filePath }}</span>
          </v-toolbar-title>

          <v-spacer />

          Also found in:
        </v-toolbar>
      </v-card-subtitle>
      <v-card-text>
        <textarea ref="editor" />
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import VContainer from "Vuetify/VGrid/VContainer";
import { VCard, VCardTitle, VCardSubtitle, VCardText } from "Vuetify/VCard";
import { VToolbar, VToolbarTitle } from "Vuetify/VToolbar";
import VSpacer from "Vuetify/VGrid/VSpacer";
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";
import VCheckbox from "Vuetify/VCheckbox/VCheckbox";

import CodeMirror from 'codemirror';

import { ccService } from '@cc-api';
import { Encoding } from '@cc/report-server-types';

import SelectReviewStatus from './SelectReviewStatus';

export default {
  name: 'Report',
  components: {
    VContainer, VCard, VCardTitle, VCardSubtitle, VCardText, VToolbar,
    VToolbarTitle, VSpacer, VBtn, VIcon, VCheckbox,
    SelectReviewStatus
  },
  data() {
    return {
      codemirror: null,
      sourceFile: null,
      report: null
    };
  },

  watch: {
    sourceFile() {
      this.codemirror.setValue(this.sourceFile.fileContent);
    },
    report(val) {
      ccService.getClient().getSourceFileData(val.fileId, true,
      Encoding.DEFAULT, (err, sourceFile) => {
        this.sourceFile = sourceFile;
      });
    }
  },

  mounted() {
    this.codemirror = CodeMirror.fromTextArea(this.$refs.editor, {
      lineNumbers: true,
      readOnly: true,
      mode: 'text/x-c++src',
      gutters: ['CodeMirror-linenumbers', 'bugInfo'],
      extraKeys: {},
      viewportMargin: 500
    });
    this.codemirror.setSize("100%", "100%");

    const reportId = this.$router.currentRoute.query["reportId"];
    this.loadReport(reportId);
  },

  methods: {
    loadReport(reportId) {
      ccService.getClient().getReport(reportId, (err, reportData) => {
        this.report = reportData;
      });
    }
  }
}
</script>
