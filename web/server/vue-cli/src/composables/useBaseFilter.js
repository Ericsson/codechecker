import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useStore } from "vuex";

import {
  SET_CMP_DATA,
  SET_REPORT_FILTER,
  SET_RUN_IDS
} from "@/store/mutations.type";
import { CompareData, ReportFilter } from "@cc/report-server-types";

export function useBaseFilter(namespaceRef) {
  const store = useStore();
  
  const defaultLimit = ref(10);
  const panel = ref(false);
  const reportFilterUnwatch = ref(null);
  const runIdsUnwatch = ref(null);
  const cmpDataUnwatch = ref(null);

  const runIds = computed(() => store.state[namespaceRef.value]?.runIds);
  const reportFilter = computed(
    () => store.state[namespaceRef.value]?.reportFilter
  );
  const cmpData = computed(() => store.state[namespaceRef.value]?.cmpData);
  
  const reportFilterModel = computed(() =>
    new ReportFilter(reportFilter.value));
  const runIdsModel = computed(() =>
    runIds.value ? runIds.value.slice(0) : null);
  const cmpDataModel = computed(() =>
    cmpData.value ? new CompareData(cmpData.value) : null);
  
  const setRunIds = payload =>
    store.commit(`${namespaceRef.value}/${SET_RUN_IDS}`, payload);
  const setReportFilter = payload => {
    store.commit(`${namespaceRef.value}/${SET_REPORT_FILTER}`, payload);
  };
  const setCmpData = payload =>
    store.commit(`${namespaceRef.value}/${SET_CMP_DATA}`, payload);
  
  const registerWatchers = (callbacks = {}) => {
    unregisterWatchers();
    
    reportFilterUnwatch.value = watch(reportFilterModel, (newVal, oldVal) => {
      Object.keys(newVal).forEach(key => {
        if (JSON.stringify(newVal[key]) !== JSON.stringify(oldVal[key])) {
          callbacks.onReportFilterChange?.(key, oldVal, newVal);
        }
      });
    }, { deep: true });
    
    runIdsUnwatch.value = watch(runIdsModel, (newVal, oldVal) => {
      callbacks.onRunIdsChange?.(oldVal, newVal);
    });
    
    cmpDataUnwatch.value = watch(cmpDataModel, (newVal, oldVal) => {
      if (!newVal || !oldVal) {
        return callbacks.onCmpDataChange?.(null, oldVal, newVal);
      }
      
      Object.keys(newVal).forEach(key => {
        if (JSON.stringify(newVal[key]) !== JSON.stringify(oldVal[key])) {
          return callbacks.onCmpDataChange?.(key, oldVal, newVal);
        }
      });
    }, { deep: true });
  };
  
  const unregisterWatchers = () => {
    reportFilterUnwatch.value?.();
    runIdsUnwatch.value?.();
    cmpDataUnwatch.value?.();
  };
  
  const beforeInit = () => {
    unregisterWatchers();
    setRunIds([]);
    setReportFilter(new ReportFilter());
    setCmpData(null);
  };
  
  const afterInit = (callbacks = {}) => {
    registerWatchers(callbacks);
    callbacks.initPanel?.();
  };
  
  const getUrlState = () => ({});
  const initByUrl = () => Promise.resolve();
  const updateReportFilter = () => {};
  const fetchItems = ref(() => []);
  const clear = () => {};
  const update = () => {};
  
  onBeforeUnmount(() => {
    unregisterWatchers();
  });
  
  return {
    defaultLimit,
    panel,
    runIds,
    reportFilter,
    cmpData,
    reportFilterModel,
    runIdsModel,
    cmpDataModel,
    namespaceRef,
    reportFilterUnwatch,
    runIdsUnwatch,
    cmpDataUnwatch,
    setRunIds,
    setReportFilter,
    setCmpData,
    registerWatchers,
    unregisterWatchers,
    beforeInit,
    afterInit,
    getUrlState,
    initByUrl,
    updateReportFilter,
    fetchItems,
    clear,
    update
  };
}
