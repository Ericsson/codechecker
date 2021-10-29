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

      <v-card-text>
        <v-container>
          <p v-if="labels.length === 0" class="pt-4">
            <strong>No documentation to this checker.</strong>
          </p>
          <v-row
            v-for="val in formattedLabels"
            v-else
            :key="val[0]"
          >
            <v-col cols="4" align-self="center">
              <strong>{{ formatLabel(val[0]) }}</strong>
            </v-col>
            <v-col>
              <severity-icon
                v-if="val[0] === 'severity'"
                :status="val[1]"
              />
              <a
                v-else-if="val[0] === 'doc_url' && val[1] !== 'Not available'"
                :href="val[1]"
                target="_blank"
              >
                {{ val[1] }}
              </a>
              <span v-else>
                {{ val[1] }}
              </span>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>

import { ccService, handleThriftError } from "@cc-api";
import { Checker, Severity } from "@cc/report-server-types";
import { SeverityIcon } from "@/components/Icons";

export default {
  name: "CheckerDocumentationDialog",
  components: {
    SeverityIcon
  },
  props: {
    value: { type: Boolean, required: true },
    checker: { type: Checker, default: null }
  },
  data() {
    return {
      labels: []
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
    },

    formattedLabels() {
      const labels = {};

      for (const label of this.labels) {
        const pos = label.indexOf(":");
        const key = label.substring(0, pos);
        const value = label.substring(pos + 1);

        if (key in labels)
          labels[key].push(value);
        else
          labels[key] = [ value ];
      }

      if ("severity" in labels)
        labels["severity"] = Severity[labels["severity"][0]];

      labels["doc_url"] =
        "doc_url" in labels ? labels["doc_url"][0] : "Not available";

      for (const key in labels) {
        if (Array.isArray(labels[key]))
          labels[key] = labels[key].join(", ");
      }

      return Object.entries(labels).sort();
    }
  },

  watch: {
    value() {
      this.getCheckerDoc();
    }
  },

  methods: {
    getCheckerDoc() {
      ccService.getClient().getCheckerLabels([ this.checker ],
        handleThriftError(labels => this.labels = labels[0]));
    },

    formatLabel(key) {
      switch (key) {
      case "profile":
        return "Profile";
      case "severity":
        return "Severity";
      case "doc_url":
        return "Documentation URL";
      case "guideline":
        return "Covered guideline";
      default:
        return key;
      }
    }
  }
};
</script>
