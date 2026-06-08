<template>
  <v-container>
    <edit-cleanup-plan-dialog
      :value.sync="editDialog"
      :cleanup-plan="selected"
      @save:cleanup-plan="fetchCleanupPlans"
    />

    <remove-cleanup-plan-dialog
      :value.sync="removeDialog"
      :cleanup-plan="selected"
      @on:confirm="fetchCleanupPlans"
    />

    <v-toolbar flat>
      <v-row>
        <v-col class="pa-0" align="right">
          <v-btn
            icon
            title="Reload cleanup plans"
            color="primary"
            @click="fetchCleanupPlans"
          >
            <v-icon>mdi-refresh</v-icon>
          </v-btn>

          <v-btn
            color="primary"
            class="new-cleanup-plan-btn mr-2"
            outlined
            @click="newCleanupPlan"
          >
            New
          </v-btn>
        </v-col>
      </v-row>
    </v-toolbar>

    <cleanup-plan-tab v-model="tab">
      <template v-slot:open>
        <list-cleanup-plans-table
          :value="openCleanupPlans || []"
          :loading="loading"
          :hide-cols="[ 'closedAt' ]"
          @edit="editCleanupPlan"
          @reopen="reopenCleanupPlan"
          @close="closeCleanupPlan"
          @remove="removeCleanupPlan"
        />
      </template>
      <template v-slot:closed>
        <list-cleanup-plans-table
          :value="closedCleanupPlans || []"
          :loading="loading"
          :hide-cols="[ 'dueDate' ]"
          @edit="editCleanupPlan"
          @reopen="reopenCleanupPlan"
          @close="closeCleanupPlan"
          @remove="removeCleanupPlan"
        />
      </template>
    </cleanup-plan-tab>
  </v-container>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import CleanupPlanTab from "./CleanupPlanTab";
import CleanupPlanTabMixin from "./CleanupPlanTab.mixin";
import EditCleanupPlanDialog from "./EditCleanupPlanDialog";
import RemoveCleanupPlanDialog from "./RemoveCleanupPlanDialog";
import ListCleanupPlansTable from "./ListCleanupPlansTable.vue";

export default {
  name: "ListCleanupPlans",
  components: {
    CleanupPlanTab,
    EditCleanupPlanDialog,
    ListCleanupPlansTable,
    RemoveCleanupPlanDialog
  },
  mixins: [ CleanupPlanTabMixin ],
  data() {
    return {
      selected: null,
      editDialog: false,
      removeDialog: false,
    };
  },

  created() {
    this.fetchCleanupPlans();
  },

  methods: {
    editCleanupPlan(cleanupPlan) {
      this.selected = cleanupPlan;
      this.editDialog = true;
    },

    newCleanupPlan() {
      this.selected = null;
      this.editDialog = true;
    },

    removeCleanupPlan(cleanupPlan) {
      this.selected = cleanupPlan;
      this.removeDialog = true;
    },

    closeCleanupPlan(cleanupPlan) {
      this.loading = true;
      ccService.getClient().closeCleanupPlan(cleanupPlan.id,
        handleThriftError(() => {
          this.loading = false;
          this.fetchCleanupPlans();

          // If a cleanup is reopened, we need to reload the closed cleanups.
          this.closedCleanupPlans = null;
        }));
    },

    reopenCleanupPlan(cleanupPlan) {
      this.loading = true;
      ccService.getClient().reopenCleanupPlan(cleanupPlan.id,
        handleThriftError(() => {
          this.loading = false;
          this.fetchCleanupPlans();

          // If a cleanup is reopened, we need to reload the opened cleanups.
          this.openCleanupPlans = null;
        }));
    },
  }
};
</script>
