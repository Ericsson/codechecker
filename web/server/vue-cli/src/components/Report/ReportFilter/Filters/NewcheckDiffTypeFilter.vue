<template>
  <select-option
    title="Diff type"
    :items="items"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :loading="loading"
    :multiple="false"
    @clear="clear"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-select-compare
      </v-icon>
    </template>

    <template v-slot:no-items>
      <v-list-item-icon>
        <v-icon>mdi-alert-outline</v-icon>
      </v-list-item-icon>
      At least one run should be selected at Newcheck!
    </template>
  </select-option>
</template>

<script>
import { ccService } from "@cc-api";
import { CompareData, DiffType } from "@cc/report-server-types";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "NewcheckDiffTypeFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "diff-type"
    };
  },

  methods: {
    encodeValue(diffType) {
      switch (parseInt(diffType)) {
        case DiffType.NEW:
          return "New";
        case DiffType.RESOLVED:
          return "Resolved";
        case DiffType.UNRESOLVED:
          return "Unresolved";
        default:
          console.warn("Non existing diff type code: ", diffType);
          return "Unknown";
      }
    },

    decodeValue(diffTypeStr) {
      return DiffType[diffTypeStr.replace(" ", "_").toUpperCase()];
    },

    updateReportFilter() {
      // TODO
    },

    onReportFilterChange(/* key */) {
      this.fetchItems();
    },

    fetchItems() {
      this.loading = true;

      if (!this.cmpData) {
        this.items = [];
        this.loading = false;
        return;
      }

      const query = Object.keys(DiffType).map(key => {
        const cmpData = new CompareData(this.cmpData);
        cmpData.diffType = DiffType[key];

        return new Promise(resolve => {
          ccService.getClient().getRunResultCount(this.runIds,
          this.reportFilter, cmpData, (err, res) => {
            resolve({ [key]: res });
          });
        });
      });

      Promise.all(query).then(res => {
        this.items = Object.keys(DiffType).map((key, index) => {
          const id = DiffType[key];
          return {
            id: id,
            title: this.titleFormatter(id),
            count: res[index][key]
          };
        });

        this.updateSelectedItems();
        this.loading = false;
      });
    },

    titleFormatter(diffType) {
      switch (diffType) {
        case DiffType.NEW:
          return "Only in Newcheck";
        case DiffType.RESOLVED:
          return "Only in Baseline";
        case DiffType.UNRESOLVED:
          return "Both in Baseline and Newcheck";
        default:
          return "Unknown";
      }
    }
  }
};
</script>
