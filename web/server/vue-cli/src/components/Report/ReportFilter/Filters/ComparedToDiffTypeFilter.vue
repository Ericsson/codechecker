<template>
  <select-option
    :id="id"
    title="Diff type"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :loading="loading"
    :multiple="false"
    :panel="panel"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <v-icon color="grey">
        {{ item.icon }}
      </v-icon>
    </template>

    <template v-slot:no-items>
      <v-list-item-icon>
        <v-icon>mdi-alert-outline</v-icon>
      </v-list-item-icon>
      At least one run should be selected at Compare to!
    </template>
  </select-option>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { CompareData, DiffType } from "@cc/report-server-types";

import SelectOption from "./SelectOption/SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";

export default {
  name: "ComparedToDiffTypeFilter",
  components: {
    SelectOption
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "diff-type",
      defaultValues: [ this.encodeValue(DiffType.NEW) ]
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
      this.setCmpData({
        diffType: this.selectedItems[0].id
      });
    },

    onCmpDataChange(key) {
      if (key === "diff-type") return;
      this.update();
    },

    getIconClass(id) {
      switch (id) {
      case DiffType.NEW:
        return "mdi-set-right";
      case DiffType.RESOLVED:
        return "mdi-set-left";
      case DiffType.UNRESOLVED:
        return "mdi-set-all";
      default:
        console.warn("Unknown diff type: ", id);
      }
    },

    fetchItems() {
      this.loading = true;

      if (!this.cmpData || !(this.cmpData.runIds || this.cmpData.runTag ||
          this.cmpData.openReportsDate)
      ) {
        this.loading = false;
        return Promise.resolve([]);
      }

      const query = Object.keys(DiffType).map(key => {
        const cmpData = new CompareData(this.cmpData);
        cmpData.diffType = DiffType[key];

        return new Promise(resolve => {
          ccService.getClient().getRunResultCount(this.runIds,
            this.reportFilter, cmpData, handleThriftError(res => {
              resolve({ [key]: res });
            }));
        });
      });

      return new Promise(resolve => {
        Promise.all(query).then(res => {
          resolve(Object.keys(DiffType).map((key, index) => {
            const id = DiffType[key];
            return {
              id: id,
              title: this.titleFormatter(id),
              count: res[index][key].toNumber(),
              icon: this.getIconClass(id)
            };
          }));
          this.loading = false;
        });
      });
    },

    titleFormatter(diffType) {
      switch (diffType) {
      case DiffType.NEW:
        return "Only in Compare to";
      case DiffType.RESOLVED:
        return "Only in Baseline";
      case DiffType.UNRESOLVED:
        return "Both in Baseline and Compare to";
      default:
        return "Unknown";
      }
    },

    // Override the default clear function because one item has to be always
    // selected for this filter.
    clear() {}
  }
};
</script>
