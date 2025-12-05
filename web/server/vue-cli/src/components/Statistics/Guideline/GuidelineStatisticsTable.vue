<template>
  <base-statistics-table
    :headers="tableHeaders"
    :items="itemsWithUuid"
    :loading="loading"
    :mobile-breakpoint="1000"
    :item-class="getRowClass"
    loading-text="Loading guideline statistics..."
    no-data-text="No guideline statistics available"
    item-key="uuid"
    :sort-by="[{ key: 'checkers.severity', order: 'desc' }]"
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
    title: "Related Checker(s)",
    key: "checkers.name"
  },
  {
    title: "Checker Severity",
    key: "checkers.severity",
    align: "center"
  },
  {
    title: "Checker Status",
    key: "checkers.enabledInAllRuns",
    align: "center"
  },
  {
    title: "Closed Reports",
    key: "checkers.closed",
    align: "center"
  },
  {
    title: "Outstanding Reports",
    key: "checkers.outstanding",
    align: "center"
  },
];

const hasTitle = computed(function() {
  return props.items.some(_item => _item.guidelineRuleTitle);
});

const tableHeaders = computed(function() {
  if (!headers) return;

  return headers.filter(_header => {
    if (_header.value === "guidelineRuleTitle") {
      return hasTitle.value;
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
$class-name: ".checker-statistics > :deep(.v-data-table__wrapper)";
@use "@/components/Statistics/style.scss";
</style>