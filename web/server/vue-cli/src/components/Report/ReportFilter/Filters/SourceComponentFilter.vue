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
      @clear="clear(true)"
      @input="setSelectedItems"
    >
      <template v-slot:prepend-toolbar-items>
        <v-btn
          class="manage-components-btn"
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

      <template v-slot:title="{ item }">
        <v-tooltip
          right
          color="white"
        >
          <template v-slot:activator="{ on, attrs }">
            <v-list-item-title
              class="mr-1 filter-item-title"
              :title="item.title"
              v-bind="attrs"
              v-on="on"
            >
              {{ item.title }}
            </v-list-item-title>
          </template>

          <v-card
            v-if="item.value"
            class="mx-auto"
            outlined
          >
            <v-list-item
              v-for="value in item.value.split('\n')"
              :key="value"
              :class="[ value[0] === '+' ? 'include' : 'exclude' ]"
              dense
            >
              {{ value }}
            </v-list-item>
          </v-card>
        </v-tooltip>
      </template>
    </select-option>
  </manage-source-component-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

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
                value: component.value
              };
            }));
            this.loading = false;
          }));
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.v-tooltip__content {
  padding: 0px;

  .v-list-item {
    min-height: auto;
  }

  .theme--light.v-list-item {
    &.include {
      color: green !important;
    }

    &.exclude {
      color: red !important;
    }
  }
}
</style>