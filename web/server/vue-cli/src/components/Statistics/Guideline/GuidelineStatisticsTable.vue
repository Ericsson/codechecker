<template>
  <base-statistics-table
    class="guideline-statistics-table"
    :headers="tableHeaders"
    :items="itemsWithUuid"
    :loading="loading"
    :mobile-breakpoint="1000"
    loading-text="Loading guideline statistics..."
    item-key="uuid"
    :sort-by="[{ key: 'checkers.severity', order: 'desc' }]"
    :item-class="getRowClass"
    no-data-text="No guideline statistics available"
    @enabled-click="enabledClick"
  />
</template>

<script setup>
import { computed } from "vue";

import { BaseStatisticsTable } from "@/components/Statistics";
import { v4 as uuidv4 } from "uuid";

const props = defineProps({
  items: { type: Array, required: true },
  loading: { type: Boolean, default: false }
});

const emit = defineEmits([ "enabled-click" ]);

function getNestedSortValue(checkers, prop) {
  if (!checkers || checkers.length === 0) {
    return prop === "name" ? "" : -1;
  }

  if (prop === "enabledInAllRuns") {
    return checkers.reduce((max, current) =>
      current.enabledRunLength > max.enabledRunLength ? current : max
    ).enabledRunLength;
  }

  return checkers.reduce((max, current) =>
    current[prop] > max[prop] ? current : max
  )[prop];
}

function checkersSortRaw(prop) {
  return (a, b) => {
    const aVal = getNestedSortValue(a.checkers, prop);
    const bVal = getNestedSortValue(b.checkers, prop);

    if (aVal < bVal) return -1;
    if (aVal > bVal) return 1;
    return 0;
  };
}

const headers = [
  {
    title: "Guideline Name",
    key: "guidelineName"
  },
  {
    title: "Rule Name",
    key: "guidelineRule"
  },
  {
    title: "Title",
    key: "guidelineRuleTitle"
  },
  {
    title: "Level",
    key: "guidelineLevel"
  },
  {
    title: "Related Checker(s)",
    key: "checkers.name",
    sortRaw: checkersSortRaw("name")
  },
  {
    title: "Checker Severity",
    key: "checkers.severity",
    align: "center",
    sortRaw: checkersSortRaw("severity")
  },
  {
    title: "Checker Status",
    key: "checkers.enabledInAllRuns",
    align: "center",
    sortRaw: checkersSortRaw("enabledInAllRuns")
  },
  {
    title: "Closed Reports",
    key: "checkers.closed",
    align: "center",
    sortRaw: checkersSortRaw("closed")
  },
  {
    title: "Outstanding Reports",
    key: "checkers.outstanding",
    align: "center",
    sortRaw: checkersSortRaw("outstanding")
  },
];

const hasTitle = computed(function() {
  return props.items.some(_item => _item.guidelineRuleTitle);
});

const hasLevel = computed(function() {
  return props.items.some(_item => _item.guidelineLevel);
});

const tableHeaders = computed(function() {
  if (!headers) return;

  return headers.filter(_header => {
    if (_header.key === "guidelineRuleTitle") {
      return hasTitle.value;
    } else if (_header.key === "guidelineLevel") {
      return hasLevel.value;
    }

    return true;
  });
});

const itemsWithUuid = computed(function() {
  return props.items.map(_item => ({
    ..._item,
    uuid: _item.uuid || uuidv4()
  }));
});

function enabledClick(_type, _checker_name) {
  emit("enabled-click", _type, _checker_name);
}

function getRowClass(item) {
  const _hasOutstanding = item.checkers.some(
    _checker => _checker.outstanding > 0);
  return _hasOutstanding ? "highlight-row" : "";
}
</script>

<style lang="scss">
@use "@/components/Statistics/style.scss" with (
  $class-name: ".guideline-statistics-table"
);
</style>
