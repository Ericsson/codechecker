<template>
  <manage-source-component-dialog
    :value.sync="dialog"
  >
    <select-option
      title="Source component"
      :items="items"
      :fetch-items="fetchItems"
      :selected-items="selectedItems"
      :search="search"
      :loading="loading"
      @clear="clear"
    >
      <template v-slot:prepend-toolbar-items>
        <v-btn
          icon
          small
          @click="dialog = true"
        >
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </template>

      <template v-slot:icon>
        <v-icon color="grey">
          mdi-puzzle-outline
        </v-icon>
      </template>
    </select-option>
  </manage-source-component-dialog>
</template>

<script>
import { ccService } from "@cc-api";

import {
  ManageSourceComponentDialog
} from "@/components/Report/SourceComponent";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "SourceComponentFilter",
  components: {
    ManageSourceComponentDialog,
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "source-component",
      search: {
        placeHolder : "Search for source components...",
        filterItems: this.filterItems
      },
      dialog: false
    };
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        componentNames: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "componentNames" || !this.selectedItems.length) return;

      this.fetchItems();
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
