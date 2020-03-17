<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="600px"
  >
    <template v-slot:activator="{ on }">
      <v-row>
        <v-col
          cols="auto"
          class="pa-0 mx-4"
        >
          <v-btn
            color="primary"
            outlined
            small
            v-on="on"
          >
            <v-icon
              class="mr-1"
              small
            >
              mdi-file-document-box-outline
            </v-icon>
            Show documentation
          </v-btn>
        </v-col>
      </v-row>
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Documentation

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <!-- eslint-disable vue/no-v-html -->
        <v-container v-html="doc" />
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
  name: "ShowDocumentationButton",
  props: {
    value: { type: String, default: null }
  },
  data() {
    return {
      dialog: false,
      doc: null,
      markedOptions: {
        highlight: function(code) {
          return hljs.highlightAuto(code).value;
        }
      }
    };
  },
  watch: {
    dialog() {
      if (!this.doc) {
        // TODO: Same logic can be found in Reports component.
        ccService.getClient().getCheckerDoc(this.value,
          handleThriftError(doc => {
            this.doc = marked(doc, this.markedOptions);
          }));
      }
    },

    value() {
      this.doc = null;
    }
  }
};
</script>