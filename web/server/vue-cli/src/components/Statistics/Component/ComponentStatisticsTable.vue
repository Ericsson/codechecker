<template>
  <base-statistics-table
    class="component-statistics"
    :headers="headers"
    :items="items"
    :loading="loading"
    :mobile-breakpoint="1000"
    :total-columns="totalColumns"
    loading-text="Loading component statistics..."
    no-data-text="No component statistics available"
    item-key="component"
    show-expand
    :expanded.sync="expanded"
    @item-expanded="itemExpanded"
  >
    <template v-slot:expanded-item="{ item }">
      <expanded-item :item="item" :colspan="headers.length" />
    </template>

    <template
      v-for="(_, slot) of $scopedSlots"
      v-slot:[slot]="scope"
    >
      <slot :name="slot" v-bind="scope" />
    </template>
  </base-statistics-table>
</template>

<script>
import { ReportFilter } from "@cc/report-server-types";
import {
  BaseStatisticsTable,
  getCheckerStatistics
} from "@/components/Statistics";
import ExpandedItem from "./ExpandedItem";

export default {
  name: "ComponentStatisticsTable",
  components: {
    BaseStatisticsTable,
    ExpandedItem
  },
  props: {
    items: { type: Array, required: true },
    loading: { type: Boolean, default: false },
    totalColumns: { type: Array, default: undefined },
    filters: { type: Object, default: () => {} }
  },
  data() {
    return {
      expanded: [],
      headers: [
        {
          text: "",
          value: "data-table-expand"
        },
        {
          text: "Component",
          value: "component",
          align: "center"
        },
        {
          text: "Unreviewed",
          value: "unreviewed.count",
          align: "center"
        },
        {
          text: "Confirmed bug",
          value: "confirmed.count",
          align: "center"
        },
        {
          text: "Outstanding reports",
          value: "outstanding.count",
          align: "center"
        },
        {
          text: "False positive",
          value: "falsePositive.count",
          align: "center"
        },
        {
          text: "Intentional",
          value: "intentional.count",
          align: "center"
        },
        {
          text: "Suppressed reports",
          value: "suppressed.count",
          align: "center"
        },
        {
          text: "All reports",
          value: "reports.count",
          align: "center"
        }
      ],
    };
  },
  watch: {
    loading() {
      if (this.loading) return;

      this.expanded.forEach(e => {
        const item = this.items.find(i => i.component === e.component);
        this.itemExpanded({ item : item });
      });
    }
  },
  methods: {
    async itemExpanded(expandedItem) {
      if (expandedItem.item.checkerStatistics) return;

      expandedItem.item.loading = true;

      const component = expandedItem.item.component;
      const runIds = this.filters.runIds;
      const reportFilter = new ReportFilter(this.filters.reportFilter);
      reportFilter["componentNames"] = [ component ];
      const cmpData = this.filters.cmpData;

      const stats = await getCheckerStatistics(runIds, reportFilter, cmpData);
      expandedItem.item.checkerStatistics = stats.map(stat => ({
        ...stat,
        $queryParams: { "source-component": component }
      }));
      expandedItem.item.loading = false;
    },
  }
};
</script>

<style lang="scss" scoped>
$class-name: ".component-statistics > ::v-deep .v-data-table__wrapper";
@import "@/components/Statistics/style.scss";
</style>
