<template>
  <v-dialog
    v-model="dialog"
    content-class="manage-cleanup-plan-dialog"
    max-width="600px"
    transition="dialog-bottom-transition"
    fullscreen
    hide-overlay
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
        <v-container>
          <v-row>
            Manage cleanup plans
          </v-row>

          <v-row>
            <cleanup-plan-subtitle />
          </v-row>
        </v-container>

        <v-spacer />

        <v-btn class="close-btn" icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <list-cleanup-plans />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="error"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import CleanupPlanSubtitle from "./CleanupPlanSubtitle";
import ListCleanupPlans from "./ListCleanupPlans";

export default {
  name: "ManageCleanupPlanDialog",
  components: {
    CleanupPlanSubtitle,
    ListCleanupPlans
  },
  props: {
    value: { type: Boolean, default: false },
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
  }
};
</script>