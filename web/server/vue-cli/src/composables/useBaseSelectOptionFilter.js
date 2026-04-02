import { ref } from "vue";
import { useRoute } from "vue-router";
import mitt from "mitt";

import { useBaseFilter } from "@/composables/useBaseFilter";

export function useBaseSelectOptionFilter(namespaceRef) {
  const route = useRoute();
  const baseFilter = useBaseFilter(namespaceRef);

  const id = ref("");
  const selectedItems = ref([]);
  const loading = ref(false);
  const defaultValues = ref(null);

  const bus = mitt();

  const setSelectedItems = (items, updateUrl = true) => {
    selectedItems.value = items;
    updateReportFilter.value();

    if (updateUrl) {
      bus.emit("update:url");
    }
  };

  const encodeValue = ref(value => value);
  const decodeValue = ref(value => value);
  const titleFormatter = ref(id => encodeValue.value(id));
  const getIconClass = ref(() => {});

  const getUrlState = () => {
    const tmpSelectedItems =
      !Array.isArray(selectedItems.value) ?
        [ selectedItems.value ] : selectedItems.value;
    const state = tmpSelectedItems.map(item => encodeValue.value(item.id));
    return { [id.value]: state.length ? state : undefined };
  };

  const initCheckOptionsByUrl = () => {
    let state = route.query[id.value];
    if (!state) {
      state = [];
    } else if (!Array.isArray(state)) {
      state = [ state ];
    }
    
    if (!state.length && defaultValues.value) {
      state = defaultValues.value;
    }

    if (!state.length) return;

    const items = state.map(s => {
      const itemId = decodeValue.value(s);
      return {
        id: itemId,
        title: titleFormatter.value(itemId),
        count: "N/A",
        icon: getIconClass.value(itemId)
      };
    });

    setSelectedItems(items, false);
  };

  const initByUrl = () => {
    initCheckOptionsByUrl();
  };

  const afterInit = async () => {
    baseFilter.registerWatchers({
      onRunIdsChange: update,
      onReportFilterChange: update
    });
    update();
    initPanel();
  };

  const initPanel = () => {
    baseFilter.panel.value = selectedItems.value.length > 0;
  };

  const update = async () => {
    bus.emit("update");

    if (!selectedItems.value.length) return;

    const items = await fetchItems.value({
      limit: selectedItems.value.length,
      query: selectedItems.value.map(item => item.id)
    });

    selectedItems.value.forEach(selectedItem => {
      const item = items.find(i => i.id === selectedItem.id);
      selectedItem.count = item ? item.count : null;
      selectedItem.value = item ? item.value : null;
    });
  };

  const filterItems = value => {
    return fetchItems.value({ query: value ? [ `${value}*` ] : null });
  };

  const clear = updateUrl => {
    setSelectedItems([], updateUrl);
  };

  // Placeholder for fetchItems - needs to be implemented by specific filter
  const fetchItems = ref(() => Promise.resolve([]));
  const updateReportFilter = ref(() => {});

  return {
    ...baseFilter,
    id,
    selectedItems,
    bus,
    loading,
    defaultValues,
    setSelectedItems,
    encodeValue,
    decodeValue,
    titleFormatter,
    getUrlState,
    getIconClass,
    initByUrl,
    afterInit,
    initPanel,
    update,
    filterItems,
    clear,
    fetchItems,
    updateReportFilter,
    initCheckOptionsByUrl
  };
}
