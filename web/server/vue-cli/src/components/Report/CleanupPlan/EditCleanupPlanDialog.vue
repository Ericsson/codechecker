<template>
  <v-dialog
    v-model="dialog"
    hide-overlay
    content-class="edit-cleanup-plan-dialog"
    max-width="600px"
    scrollable
  >
    <template v-slot:activator="{}">
      <slot />
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        <div
          v-if="cleanupPlan"
        >
          Edit cleanup plan
        </div>
        <div
          v-else
        >
          New cleanup plan
          <div class="subtitle-1">
            Create a new cleanup plan which helps you to fix legacy reports.
          </div>
        </div>

        <v-spacer />

        <v-btn class="close-btn" icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <v-form ref="form">
            <v-text-field
              v-model.trim="name"
              class="cleanup-plan-name"
              label="Name*"
              autofocus
              outlined
              required
              :rules="rules.name"
            />

            <due-date-menu
              :value.sync="dueDate"
            />

            <v-textarea
              v-model.trim="description"
              class="cleanup-plan-description "
              label="Description"
              outlined
            />
          </v-form>
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          class="cancel-btn"
          color="error"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          class="save-btn"
          color="primary"
          text
          @click="saveCleanupPlan"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import DueDateMenu from "./DueDateMenu";

export default {
  name: "NewCleanupPlanDialog",
  components: {
    DueDateMenu
  },
  props: {
    value: { type: Boolean, default: false },
    cleanupPlan: { type: Object, default: () => null },
  },
  data() {
    return {
      description: null,
      dueDate: null,
      name: null,
      dueDateMenu: false,
      rules: {
        name: [ v => !!v || "Name is required" ],
        value: [
          v => !!v || "Value is required"
        ]
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
      if (!this.dialog) return;

      this.description = this.cleanupPlan?.description || null;
      this.dueDate = this.cleanupPlan?.dueDate?.toNumber() || null;
      this.name = this.cleanupPlan?.name || null;
    }
  },

  methods: {
    async saveCleanupPlan() {
      if (!this.$refs.form.validate()) return;

      if (this.cleanupPlan) {
        // Edit an existing cleanup plan.
        ccService.getClient().updateCleanupPlan(
          this.cleanupPlan.id, this.name,
          this.description, this.dueDate,
          handleThriftError(async success => {
            if (success) {
              this.$emit("save:cleanup-plan");
              this.dialog = false;
            }
          }));
      } else {
        // Add new cleanup plan.
        ccService.getClient().addCleanupPlan(
          this.name, this.description, this.dueDate,
          handleThriftError(async () => {
            this.$emit("save:cleanup-plan");
            this.dialog = false;
          }));
      }
    },

    onAPIOperationFinished(success) {
      if (success) {
        this.$emit("save:cleanup-plan");
        this.dialog = false;
      }
    }
  }
};
</script>

<style lang="scss">
.value textarea::placeholder {
  opacity: 0.5;
}
</style>
