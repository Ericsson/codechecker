<template>
  <base-statistics-table
    v-model:expanded="expanded"
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
    :necessary-total="true"
    @item-expanded="itemExpanded"
  >
    <template v-slot:expanded-item="{ item }">
      <expanded-item :item="item" :colspan="headers.length" />
    </template>

    <template
      v-for="(_, slot) of $slots"
      v-slot:[slot]="scope"
    >
      <slot :name="slot" v-bind="scope" />
    </template>
  </base-statistics-table>
</template>

<script setup>
import { ref, watch } from "vue";

import {
  BaseStatisticsTable,
  getCheckerStatistics
} from "@/components/Statistics";
import { ReportFilter } from "@cc/report-server-types";
import ExpandedItem from "./ExpandedItem";

const props = defineProps({
  items: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  totalColumns: { type: Array, default: undefined },
  filters: { type: Object, default: () => {} }
});

const expanded = ref([]);

const headers = [
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
];

watch(function() { return props.loading; }, function() {
  if (props.loading) return;

  expanded.value.forEach(_e => {
    const _item = props.items.find(_i => _i.component === _e.component);
    itemExpanded({ item : _item });
  });
});

async function itemExpanded(expandedItem) {
  if (expandedItem.item.checkerStatistics) return;

  expandedItem.item.loading = true;

  const _component = expandedItem.item.component;
  const _runIds = props.filters.runIds;
  const _reportFilter = new ReportFilter(props.filters.reportFilter);
  _reportFilter["componentNames"] = [ _component ];
  const _cmpData = props.filters.cmpData;

  const _stats = await getCheckerStatistics(_runIds, _reportFilter, _cmpData);
  expandedItem.item.checkerStatistics = _stats.map(_stat => ({
    ..._stat,
    $queryParams: { "source-component": _component }
  }));
  expandedItem.item.loading = false;
}
</script>

<style lang="scss" scoped>
$class-name: ".component-statistics > :deep(.v-data-table__wrapper)";
@use "@/components/Statistics/style.scss";
</style>
