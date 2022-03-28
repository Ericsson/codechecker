<template>
  <confirm-dialog
    v-model="dialog"
    content-class="remove-filtered-rules-dialog"
    confirm-btn-label="Remove"
    @confirm="removeReviewStatusRule"
  >
    <template v-slot:title>
      Remove filtered review status rules
    </template>

    <template v-slot:content>
      <v-container>
        <v-alert
          class="mt-2"
          color="error"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-alert-outline"
        >
          Are you sure that you would like to remove all the filtered review
          status rules (<b>{{ total }}</b>) from the database?
          <br><br>
          <b>IMPORTANT**</b>: be careful when you delete rules because this
          operation can not be undone.
        </v-alert>
      </v-container>
    </template>
  </confirm-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import { ConfirmDialog } from "@/components";

export default {
  name: "RemoveFilteredRulesDialog",
  components: { ConfirmDialog },
  props: {
    value: { type: Boolean, default: false },
    filter: { type: Object, default: null },
    total: { type: Number, default: null },
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
      ccService.getClient().removeReviewStatusRules(this.filter,
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
