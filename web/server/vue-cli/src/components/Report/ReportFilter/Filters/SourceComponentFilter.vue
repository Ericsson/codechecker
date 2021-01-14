<template>
  <manage-source-component-dialog
    :value.sync="dialog"
  >
    <select-option
      :id="id"
      title="Source component"
      :bus="bus"
      :fetch-items="fetchItems"
      :selected-items="selectedItems"
      :search="search"
      :loading="loading"
      :panel="panel"
      @clear="clear(true)"
      @input="setSelectedItems"
    >
      <template v-slot:prepend-toolbar-items>
        <v-btn
          class="manage-components-btn"
          icon
          small
          @click.stop="dialog = true"
        >
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </template>

      <template v-slot:icon>
        <v-icon color="grey">
          mdi-puzzle-outline
        </v-icon>
      </template>

      <template v-slot:title="{ item }">
        <source-component-tooltip :value="item.value">
          <template v-slot="{ on }">
            <v-list-item-title
              class="mr-1 filter-item-title"
              :title="item.title"
              v-on="on"
            >
              {{ item.title }}
            </v-list-item-title>
          </template>
        </source-component-tooltip>
      </template>
    </select-option>
  </manage-source-component-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import {
  ManageSourceComponentDialog,
  SourceComponentTooltip
} from "@/components/Report/SourceComponent";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "SourceComponentFilter",
  components: {
    ManageSourceComponentDialog,
    SelectOption,
    SourceComponentTooltip
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

  watch: {
    dialog(value) {
      if (value) return;

      // If the source component manager dialog is closed we need to update
      // the filter items to make sure that new items will be shown.
      this.bus.$emit("update");
    }
  },

  methods: {
    updateReportFilter() {
      this.setReportFilter({
        componentNames: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "componentNames") return;
      this.update();
    },

    fetchItems(opt={}) {
      this.loading = true;

      return new Promise(resolve => {
        const filter = opt.query;
        ccService.getClient().getSourceComponents(filter,
          handleThriftError(res => {
            resolve(res.map(component => {
              return {
                id : component.name,
                title: component.name,
                value: component.value || component.description
              };
            }));
            this.loading = false;
          }));
      });
    }
  }
};
</script>
