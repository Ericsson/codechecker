<template>
  <confirm-dialog
    v-model="dialog"
    max-width="600px"
    cancel-btn-color="primary"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    content-class="remove-cleanup-plan-dialog"
    @confirm="removeCleanupPlan"
  >
    <template v-slot:title>
      Remove cleanup plan
    </template>

    <template v-if="cleanupPlan" v-slot:content>
      Are you sure that you would like to remove
      <b>{{ cleanupPlan.name }}</b> cleanup plan?
    </template>
  </confirm-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import ConfirmDialog from "@/components/ConfirmDialog";

export default {
  name: "RemoveCleanupPlanDialog",
  components: {
    ConfirmDialog
  },
  props: {
    value: { type: Boolean, default: false },
    cleanupPlan: { type: Object, default: () => null }
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

  methods: {
    removeCleanupPlan() {
      ccService.getClient().removeCleanupPlan(this.cleanupPlan.id,
        handleThriftError(success => {
          if (success) {
            this.$emit("on:confirm");
            this.dialog = false;
          }
        }));
    }
  }
};
</script>
