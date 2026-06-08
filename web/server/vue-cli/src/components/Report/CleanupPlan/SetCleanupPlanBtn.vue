<template>
  <v-menu
    v-model="menu"
    content-class="set-cleanup-plan-dialog"
    :close-on-content-click="false"
    :nudge-width="100"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <div class="d-flex align-center">
        <v-btn
          v-bind="activatorProps"
          color="primary"
          class="set-cleanup-plan-btn"
          variant="outlined"
          size="small"
          :disabled="!selectedReportHashes.length"
          :loading="cleanupPlan.loading.value"
          prepend-icon="mdi-sign-direction"
        >
          Set cleanup plan
        </v-btn>

        <div class="mx-2">
          <tooltip-help-icon>
            You can use <b>cleanup plans</b> to track progress of reports in
            your product.
            <ul>
              <li>
                You can manage cleanup plans from the report filter bar
                by clicking on the pencil icon
                (<v-icon size="small" :style="{ color: 'white' }">
                  mdi-pencil
                </v-icon>)
                beside the <i>Cleanup plan</i> filter.
              </li>
              <li>
                After you created a cleanup plan, with this button you can
                associate it with selected / current report(s).
              </li>
              <li>
                You can list reports associated with a cleanup plan by using the
                <i>Cleanup plan</i> filter.
              </li>
            </ul>
          </tooltip-help-icon>
        </div>
      </div>
    </template>

    <v-card>
      <cleanup-plan-tab
        v-model="selectedTab"
      >
        <template v-slot:open>
          <cleanup-plan-list
            :cleanup-plans="cleanupPlan.openCleanupPlans.value"
            :selected-plans="changedSelectedItems"
            :not-all-selected="changedNotAllSelected"
            @update:selected-plans="updateSelectedCleanupPlans"
          />
        </template>

        <template v-slot:closed>
          <cleanup-plan-list
            :cleanup-plans="cleanupPlan.closedCleanupPlans.value"
            :selected-plans="changedSelectedItems"
            :not-all-selected="changedNotAllSelected"
            @update:selected-plans="updateSelectedCleanupPlans"
          />
        </template>
      </cleanup-plan-tab>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, ref, watch } from "vue";

import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { useCleanupPlan } from "@/composables/useCleanupPlan";
import CleanupPlanList from "./CleanupPlanList";
import CleanupPlanTab from "./CleanupPlanTab";

const props = defineProps({
  selectedReports: { type: Array, required: true }
});

const menu = ref(false);
const origSelectedItems = ref([]);
const changedSelectedItems = ref([]);
const origNotAllSelected = ref({});
const changedNotAllSelected = ref({});
const cleanupPlan = useCleanupPlan();
const selectedTab = ref(0);

const selectedReportHashes = computed(() => {
  if (!props.selectedReports) return [];
  const bugHashesArray = props.selectedReports.map(item => item.bugHash);
  const bugHashSet = Array.from(new Set(bugHashesArray));
  return bugHashSet;
});

watch(menu, () => {
  if (!menu.value) {
    save();
    reset();
  } else {
    cleanupPlan.fetchCleanupPlans(true, onFetchFinished);
  }
});

watch(selectedTab, () => {
  cleanupPlan.tab.value = selectedTab.value;
});

function reset() {
  cleanupPlan.openCleanupPlans.value = null;
  cleanupPlan.closedCleanupPlans.value = null;
  origSelectedItems.value = [];
  changedSelectedItems.value = [];
  origNotAllSelected.value = {};
  changedNotAllSelected.value = {};
}

function save() {
  getCheckedCleanups().forEach(cleanupPlanId => {
    ccService.getClient().setCleanupPlan(
      cleanupPlanId,
      selectedReportHashes.value,
      handleThriftError()
    );
  });

  getUncheckedCleanups().forEach(cleanupPlanId => {
    ccService.getClient().unsetCleanupPlan(
      cleanupPlanId,
      selectedReportHashes.value,
      handleThriftError()
    );
  });
}

function getCheckedCleanups() {
  return changedSelectedItems.value.filter(s =>
    !origSelectedItems.value.includes(s));
}

function getUncheckedCleanups() {
  const _removeFromCleanups = [];

  origSelectedItems.value.forEach(s => {
    if (!changedSelectedItems.value.includes(s)) {
      _removeFromCleanups.push(s);
    }
  });
  Object.keys(origNotAllSelected.value).forEach(s => {
    if (
      !(s in changedNotAllSelected.value) &&
      !changedSelectedItems.value.includes(s)
    ) {
      _removeFromCleanups.push(s);
    }
  });

  return _removeFromCleanups;
}

function onFetchFinished(cleanupPlans) {
  cleanupPlans.forEach(plan => {
    const planId = plan.id.toNumber();

    const planHashes = new Set(plan.reportHashes);
    const commonReportHashes = selectedReportHashes.value.filter(
      reportHash => planHashes.has(reportHash));

    if (
      commonReportHashes.length === selectedReportHashes.value.length
    ) {
      // Every selected report hashes are in the current cleanup plan so
      // mark it as active.
      if (!origSelectedItems.value.includes(planId)) {
        origSelectedItems.value.push(planId);
        changedSelectedItems.value.push(planId);
      }
    } else if (commonReportHashes.length !== 0) {
      // Not all selected report hashes are in the cleanup plan, so mark
      // it differently.
      origNotAllSelected.value[planId] = true;
      changedNotAllSelected.value[planId] = true;
    }
  });
}

function updateSelectedCleanupPlans(_cleanupPlanIds) {
  _cleanupPlanIds.forEach(id => {
    if (!changedSelectedItems.value.includes(id)) {
      delete changedNotAllSelected.value[id];
    }
  });

  changedSelectedItems.value = _cleanupPlanIds;
}
</script>
