<template>
  <confirm-dialog
    v-model="dialog"
    content-class="edit-review-status-rule-dialog"
    scrollable
    @confirm="saveReviewStatusRule"
  >
    <template v-slot:title>
      <span
        v-if="rule"
      >
        Edit review status rule
      </span>
      <span
        v-else
      >
        New review status rule
      </span>
    </template>

    <template v-slot:content>
      <v-form ref="form">
        <v-text-field
          v-model.trim="reportHash"
          class="report-hash mb-2"
          label="Report hash*"
          autofocus
          outlined
          required
          :hide-details="true"
          :rules="rules.reportHash"
        />

        <select-review-status
          v-model="status"
          class="mb-2"
          label="Select review status*"
          :clearable="false"
          :rules="rules.selectReviewStatus"
        />

        <v-textarea
          v-model.trim="message"
          class="message pa-0"
          solo
          flat
          outlined
          name="reviewStatusMessage"
          label="(Optionally) Explain the status change..."
          :hide-details="true"
        />
      </v-form>
    </template>
  </confirm-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import { ConfirmDialog } from "@/components";
import SelectReviewStatus from "./SelectReviewStatus";

export default {
  name: "EditReviewStatusRuleDialog",
  components: { ConfirmDialog, SelectReviewStatus },
  props: {
    value: { type: Boolean, default: false },
    rule: { type: Object, default: () => null },
  },
  data() {
    return {
      reportHash: null,
      status: null,
      message: null,
      rules: {
        reportHash: [ v => !!v || "Report hash is required" ],
        selectReviewStatus: [ v => !!v || "Review status is required" ],
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
    dialog() {
      if (this.dialog) {
        this.$refs.form?.resetValidation();
      }
    },
    rule() {
      this.reportHash = this.rule?.reportHash;
      this.status = this.rule?.status;
      this.message = this.rule?.message;
    }
  },
  methods: {
    async saveReviewStatusRule() {
      if (!this.$refs.form.validate()) return;

      ccService.getClient().addReviewStatusRule(
        this.reportHash, this.status, this.message,
        handleThriftError(async () => {
          this.$emit("on:confirm");
          this.dialog = false;
        }));
    }
  }
};
</script>
