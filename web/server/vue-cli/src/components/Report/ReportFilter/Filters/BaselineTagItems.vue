<template>
  <v-container class="pa-0" fluid>
    <v-progress-linear
      v-if="baseSelectOptionFilter.loading.value"
      indeterminate
      size="64"
    />

    <items
      :items="tags"
      :selected-items="props.selectedItems"
      :search="search"
      :limit="baseSelectOptionFilter.defaultLimit"
      @apply="apply"
      @cancel="cancel"
      @select="select"
    >
      <template v-slot:append-toolbar>
        <v-container>
          <v-row class="pt-2" justify="center">
            <v-date-picker v-model="dateFilter" no-title />
          </v-row>
        </v-container>

        <bulb-message>
          Selecting a date above will filter history events stored before
          midnight of the given date.
        </bulb-message>
      </template>


      <template v-slot:title="{ item }">
        <v-list-item-title
          v-if="item.title"
          :title="item.title"
        >
          {{ item.title }}
        </v-list-item-title>
        <v-list-item-title
          v-else
          :title="'No tag name is specified for this storage. Use the ' +
            '\'--tag\' option to specify a tag name for a storage at the ' +
            '\'CodeChecker store\' command.'"
        >
          Storage without a named tag
        </v-list-item-title>

        <v-list-item-subtitle :title="`Stored on ${item.time}`">
          {{ item.time }}
        </v-list-item-subtitle>
      </template>

      <template v-slot:icon="{ item }">
        <slot name="icon" :item="item" />
      </template>
    </items>
  </v-container>
</template>

<script setup>
import { endOfDay, parse } from "date-fns";
import {
  onMounted,
  ref,
  toRef,
  watch
} from "vue";

import { ccService, handleThriftError } from "@cc-api";
import { DateInterval, ReportFilter } from "@cc/report-server-types";

import BulbMessage from "@/components/BulbMessage";
import { useBaseSelectOptionFilter }
  from "@/composables/useBaseSelectOptionFilter";

import { useDateUtils } from "@/composables/useDateUtils";
import Items from "./SelectOption/Items";

const props = defineProps({
  namespace: { type: String, required: true },
  runId: { type: Number, required: true },
  selectedItems: { type: Array, default: null },
  limit: { type: Number, required: true }
});
const emit = defineEmits([
  "apply",
  "select",
  "cancel"
]);
const search = ref({
  placeHolder : "Search by tag name...",
  filterItems: filterItems
});
const tags = ref([]);
const dateFilter = ref(null);
const filterOpt = ref({});

const { getUnixTime, prettifyDate } = useDateUtils();

const baseSelectOptionFilter = useBaseSelectOptionFilter(
  toRef(props, "namespace")
);

watch(() => props.runId, async () => {
  tags.value = await fetchTags(filterOpt.value);
});

watch(dateFilter, async () => {
  tags.value = await fetchTags(filterOpt.value);
});

onMounted(async () => {
  tags.value = await fetchTags(filterOpt.value);
});

async function getRunTagFilter() {
  const query = filterOpt.value.query;

  if (!query && !dateFilter.value)
    return null;

  let stored = null;
  if (dateFilter.value) {
    const date = parse(dateFilter.value, "yyyy-MM-dd", new Date());
    const midnight = endOfDay(date);

    stored = new DateInterval({
      before: getUnixTime(midnight)
    });
  }

  const tags =
    await ccService.getTags([ props.runId ], null, query, stored);

  return tags.map(_t => _t.id.toNumber());
}

async function fetchTags(opt={}) {
  baseSelectOptionFilter.loading.value = true;
  filterOpt.value = opt;

  const _reportFilter = new ReportFilter(
    baseSelectOptionFilter.reportFilter.value
  );
  const _limit = opt.limit || props.limit;
  const _offset = 0;

  _reportFilter.runTag = await getRunTagFilter();

  return new Promise((resolve, reject) => {
    ccService.getClient().getRunHistoryTagCounts(
      [ props.runId ],
      baseSelectOptionFilter.reportFilter.value,
      null,
      _limit,
      _offset,
      handleThriftError(res => {
        resolve(res.map(tag => {
          const id = tag.id.toNumber();
          const time = prettifyDate(tag.time);
          return {
            id,
            runName: tag.runName,
            runId: tag.runId.toNumber(),
            tagName: tag.name || time,
            time: time,
            title: tag.name,
            count: tag.count.toNumber()
          };
        }));

        baseSelectOptionFilter.loading.value = false;
      },
      err => {
        baseSelectOptionFilter.loading.value = false;
        reject(err);
      }));
  });
}

function filterItems(value) {
  return fetchTags({ query: value ? [ `${value}*` ] : null });
}

function apply(selected) {
  emit("apply", selected);
}

function select(selectedItems) {
  emit("select", selectedItems);
}

function cancel() {
  emit("cancel");
}

defineExpose({
  filterItems,
  apply,
  select,
  cancel
});
</script>

<style lang="scss" scoped>
:deep(.v-date-picker-table) {
  height: 210px;
}
</style>
