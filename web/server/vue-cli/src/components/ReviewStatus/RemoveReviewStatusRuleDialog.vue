<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="remove-review-status-rule-dialog"
    confirm-btn-label="Remove"
    title="Remove review status rule"
    @confirm="removeReviewStatusRule"
  >
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
          border="start"
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
  </ConfirmDialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { ReviewStatusRuleFilter } from "@cc/report-server-types";
import { computed } from "vue";

import { ConfirmDialog } from "@/components";

const props = defineProps({
  value: { type: Boolean, default: false },
  rule: { type: Object, default: () => null },
});

const emit = defineEmits([ "update:value", "on:confirm" ]);

const dialog = computed({
  get() {
    return props.value;
  },
  set(val) {
    emit("update:value", val);
  }
});

function removeReviewStatusRule() {
  const _filter = new ReviewStatusRuleFilter();
  _filter.reportHashes = [ props.rule.reportHash ];

  ccService.getClient().removeReviewStatusRules(_filter,
    handleThriftError(success => {
      if (success) {
        emit("on:confirm", props.rule);
        dialog.value = false;
      }
    }));
}
</script>
