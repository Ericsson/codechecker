<template>
  <confirm-dialog
    v-model="dialog"
    content-class="remove-review-status-rule-dialog"
    confirm-btn-label="Remove"
    @confirm="removeReviewStatusRule"
  >
    <template v-slot:title>
      Remove review status rule
    </template>

    <template v-slot:content>
      <v-container
        v-if="rule"
      >
        Are you sure that you would like to remove review status rule for
        report hash <b>{{ rule.reportHash }}</b>?

        <v-alert
          v-if="rule.associatedReportCount"
          class="mt-2"
          color="error"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-alert-outline"
        >
          There
          <span v-if="rule.associatedReportCount === 1">is</span>
          <span v-else>are</span>
          <b>{{ rule.associatedReportCount }}</b> matching
          <span v-if="rule.associatedReportCount === 1">report</span>
          <span v-else>reports</span>
          associated with this rule. Removing a review status rule
          will change the review statuses of these reports back to
          <i>Unreviewed</i>, so they become outstanding at the current date.
          This may affect statistics as well. The operation can't be undone.
        </v-alert>
      </v-container>
    </template>
  </confirm-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { ReviewStatusRuleFilter } from "@cc/report-server-types";

import { ConfirmDialog } from "@/components";

export default {
  name: "RemoveReviewStatusRuleDialog",
  components: { ConfirmDialog },
  props: {
    value: { type: Boolean, default: false },
    rule: { type: Object, default: () => null },
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
  },
  methods: {
    removeReviewStatusRule() {
      const filter = new ReviewStatusRuleFilter();
      filter.reportHashes = [ this.rule.reportHash ];

      ccService.getClient().removeReviewStatusRules(filter,
        handleThriftError(success => {
          if (success) {
            this.$emit("on:confirm", this.rule);
            this.dialog = false;
          }
        }));
    }
  }
};
</script>
