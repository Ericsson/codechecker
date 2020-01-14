<template>
  <v-container fluid>
    <textarea ref="editor" />
  </v-container>
</template>

<script>
import VContainer from "Vuetify/VGrid/VContainer";

import CodeMirror from 'codemirror';

import { ccService } from '@cc-api';
import { Encoding } from '@cc/report-server-types';

export default {
  name: 'Report',
  components: {
    VContainer
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
