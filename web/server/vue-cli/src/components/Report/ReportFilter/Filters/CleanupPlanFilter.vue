<template>
  <manage-cleanup-plan-dialog
    :value.sync="dialog"
  >
    <select-option
      :id="id"
      title="Cleanup plan"
      :bus="bus"
      :fetch-items="fetchItems"
      :selected-items="selectedItems"
      :loading="loading"
      :panel="panel"
      @clear="clear(true)"
      @input="setSelectedItems"
    >
      <template v-slot:prepend-toolbar-items>
        <v-btn
          class="manage-cleanup-plan-btn"
          icon
          small
          @click.stop="dialog = true"
        >
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </template>

      <template v-slot:icon>
        <v-icon color="grey">
          mdi-sign-direction
        </v-icon>
      </template>
    </select-option>
  </manage-cleanup-plan-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import {
  ManageCleanupPlanDialog
} from "@/components/Report/CleanupPlan";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "SourceComponentFilter",
  components: {
    ManageCleanupPlanDialog,
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "cleanup-plan",
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
        cleanupPlanNames: this.selectedItems.map(item => item.id)
      });
    },

    onReportFilterChange(key) {
      if (key === "cleanupPlanNames") return;
      this.update();
    },

    fetchItems() {
      this.loading = true;

      return new Promise(resolve => {
        ccService.getClient().getCleanupPlans(null, handleThriftError(res => {
          resolve(res.map(cleanupPlan => {
            return {
              id : cleanupPlan.name,
              title: cleanupPlan.name,
              value: cleanupPlan.description
            };
          }));
          this.loading = false;
        }));
      });
    }
  }
};
</script>
