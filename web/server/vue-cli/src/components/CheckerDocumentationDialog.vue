<template>
  <v-dialog
    v-model="dialog"
    content-class="documentation-dialog"
    max-width="600px"
  >
    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Checker documentation

        <v-spacer />

        <v-btn class="close-btn" icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <!-- eslint-disable vue/no-v-html -->
        <v-container v-html="docs[checkerName]" />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import hljs from "highlight.js";
import "highlight.js/styles/default.css";
import marked from "marked";

import { ccService, handleThriftError } from "@cc-api";

export default {
  name: "CheckerDocumentationDialog",
  props: {
    value: { type: Boolean, required: true },
    checkerName: { type: String, default: null },
  },
  data() {
    return {
      docs: {},
      markedOptions: {
        highlight: function(code) {
          return hljs.highlightAuto(code).value;
        }
      }
    };
  },

  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("update:value", val);
      }
    }
  },

  watch: {
    value() {
      this.getCheckerDoc();
    }
  },

  methods: {
    getCheckerDoc() {
      if (!this.dialog || this.docs[this.checkerName]) return;

      ccService.getClient().getCheckerDoc(this.checkerName,
        handleThriftError(doc => this.$set(
          this.docs, this.checkerName, marked(doc, this.markedOptions))));
    }
  }
};
</script>