// composables/useRunFilter.js
import { ref } from "vue";

import { ccService } from "@cc-api";

export function useRunFilter() {
  const selectedTagItems = ref([]);

  async function getSelectedRunIds(selectedItems) {
    return [].concat(...await Promise.all(
      selectedItems.value.map(async item => {
        if (!item.runIds) {
          item.runIds = await ccService.getRunIds(item.title);
        }
        return Promise.resolve(item.runIds);
      })));
  }

  return {
    selectedTagItems,
    getSelectedRunIds
  };
}
