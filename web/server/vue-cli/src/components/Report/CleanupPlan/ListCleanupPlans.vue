<template>
  <v-container>
    <remove-cleanup-plan-dialog
      v-model="removeDialog"
      :cleanup-plan="selected"
      @on:confirm="cleanupPlan.fetchCleanupPlans"
    />

    <v-toolbar
      elevation="0"
      color="transparent"
    >
      <v-row>
        <v-col class="d-flex justify-end align-center">
          <v-btn
            icon="mdi-refresh"
            title="Reload cleanup plans"
            color="primary"
            @click="cleanupPlan.fetchCleanupPlans"
          />

          <edit-cleanup-plan-dialog
            v-model="editDialog"
            :cleanup-plan="selected"
            @save:cleanup-plan="cleanupPlan.fetchCleanupPlans"
          />
        </v-col>
      </v-row>
    </v-toolbar>

    <cleanup-plan-tab
      v-model="selectedTab"
    >
      <template
        v-slot:open
      >
        <list-cleanup-plans-table
          :items="cleanupPlan.openCleanupPlans?.value || []"
          :loading="loading"
          :hide-cols="[ 'closedAt' ]"
          @edit="editCleanupPlan"
          @reopen="reopenCleanupPlan"
          @close="closeCleanupPlan"
          @remove="removeCleanupPlan"
        />
      </template>
      <template
        v-slot:closed
      >
        <list-cleanup-plans-table
          :items="cleanupPlan.closedCleanupPlans?.value || []"
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

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { onMounted, ref, watch } from "vue";

import { useCleanupPlan } from "@/composables/useCleanupPlan";
import CleanupPlanTab from "./CleanupPlanTab";
import EditCleanupPlanDialog from "./EditCleanupPlanDialog";
import ListCleanupPlansTable from "./ListCleanupPlansTable.vue";
import RemoveCleanupPlanDialog from "./RemoveCleanupPlanDialog";

const selected = ref(null);
const editDialog = ref(false);
const removeDialog = ref(false);
const cleanupPlan = useCleanupPlan();
const selectedTab = ref(0);

watch(selectedTab, () => {
  cleanupPlan.tab.value = selectedTab.value;
});

watch(editDialog, open => {
  if (!open) {
    selected.value = null;
  }
});

onMounted(() => {
  cleanupPlan.fetchCleanupPlans();
});

function editCleanupPlan(_cleanupPlan) {
  selected.value = _cleanupPlan;
  editDialog.value = true;
}

function removeCleanupPlan(_cleanupPlan) {
  selected.value = _cleanupPlan;
  removeDialog.value = true;
}

function closeCleanupPlan(_cleanupPlan) {
  cleanupPlan.loading.value = true;
  ccService.getClient().closeCleanupPlan(_cleanupPlan.id,
    handleThriftError(() => {
      cleanupPlan.loading.value = false;
      cleanupPlan.fetchCleanupPlans();

      // If a cleanup is reopened, we need to reload the closed cleanups.
      cleanupPlan.closedCleanupPlans.value = null;
    }));
}

function reopenCleanupPlan(_cleanupPlan) {
  cleanupPlan.loading.value = true;
  ccService.getClient().reopenCleanupPlan(_cleanupPlan.id,
    handleThriftError(() => {
      cleanupPlan.loading.value = false;
      cleanupPlan.fetchCleanupPlans();

      // If a cleanup is reopened, we need to reload the opened cleanups.
      cleanupPlan.openCleanupPlans.value = null;
    }));
}
</script>
