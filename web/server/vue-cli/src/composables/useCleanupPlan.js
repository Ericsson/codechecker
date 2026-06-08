import { ref, watch } from "vue";

import { ccService, handleThriftError } from "@cc-api";
import { CleanupPlanFilter } from "@cc/report-server-types";

export function useCleanupPlan() {
  const tab = ref(0);
  const loading = ref(false);
  const openCleanupPlans = ref(null);
  const closedCleanupPlans = ref(null);

  const getCleanupPlans = filter => {
    loading.value = true;
    return new Promise(resolve => {
      ccService.getClient().getCleanupPlans(filter,
        handleThriftError(cleanupPlans => {
          loading.value = false;
          resolve(cleanupPlans);
        }));
    });
  };

  const fetchOpenCleanupPlans = async onFetchFinished => {
    const filter = new CleanupPlanFilter({ isOpen: true });
    openCleanupPlans.value = await getCleanupPlans(filter);
    onFetchFinished?.(openCleanupPlans.value);
  };

  const fetchClosedCleanupPlans = async onFetchFinished => {
    const filter = new CleanupPlanFilter({ isOpen: false });
    closedCleanupPlans.value = await getCleanupPlans(filter);
    onFetchFinished?.(closedCleanupPlans.value);
  };

  const fetchCleanupPlans = (force = true, onFetchFinished) => {
    if (tab.value === 0) {
      if (!openCleanupPlans.value || force) {
        fetchOpenCleanupPlans(onFetchFinished);
      }
    } else {
      if (!closedCleanupPlans.value || force) {
        fetchClosedCleanupPlans(onFetchFinished);
      }
    }
  };

  watch(tab, () => {
    fetchCleanupPlans(false);
  });

  return {
    tab,
    loading,
    openCleanupPlans,
    closedCleanupPlans,
    fetchCleanupPlans,
    fetchOpenCleanupPlans,
    fetchClosedCleanupPlans
  };
}
