<template>
  <select-option
    title="Source component"
    :items="items"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-puzzle-outline
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import { ccService } from "@cc-api";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "SourceComponentFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "source-component",
      search: {
        placeHolder : "Search for source components...",
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        componentNames: this.selectedItems.map(item => item.id)
      });
    },

    fetchItems(search=null) {
      this.loading = true;

      const filter = search ? [ `${search}*` ] : null;
      ccService.getClient().getSourceComponents(filter, (err, res) => {
        this.items = res.map((component) => {
          return {
            id : component.name,
            title: component.name
          };
        });

        this.loading = false;
      });
    },

    filterItems(value) {
      this.fetchItems(value);
    }
  }
}
</script>
