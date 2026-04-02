<template>
  <select-option
    :id="id"
    title="Run / Tag Filter"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :search="search"
    :loading="baseSelectOptionFilter.loading.value"
    :apply="applySelection"
    :panel="baseSelectOptionFilter.panel.value"
    @cancel="cancelSelection"
    @select="console.log('select-option @select')"
    @clear="clear(true)"
    @on-menu-show="selectTagForRun = null"
  >
    <template v-slot:append-toolbar-title>
      <SelectedToolbarTitleItems
        v-if="selectedToolbarTitleItems.length"
        :value="selectedToolbarTitleItems"
      />
    </template>

    <template
      v-slot:menu-content="{
        items,
        prevSelectedItems,
        cancel: cancelItemSelection,
        select,
        onApplyFinished
      }"
    >
      <v-menu
        v-model="selectTagMenu"
        content-class="select-tag-menu"
        :close-on-content-click="false"
        :nudge-width="300"
        :max-width="550"
        offset-x
      >
        <template v-slot:activator="{ props: menuProps }">
          <items
            :items="items"
            :selected-items="prevSelectedItems"
            :search="search"
            :limit="defaultLimit"
            :format="formatRunTitle"
            @apply="applySelection"
            @apply:finished="onApplyFinished"
            @cancel="cancelItemSelection"
            @select="select"
            @update:items="items.splice(0, items.length, ...$event)"
          >
            <template v-slot:append-toolbar>
              <bulb-message>
                Use the <v-icon>mdi-cog</v-icon> button beside each run
                to specify a tag.
              </bulb-message>
            </template>

            <template v-slot:prepend-count="{ item }">
              <v-tooltip
                max-width="200"
                location="right"
              >
                <template v-slot:activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="{ ...tooltipProps, ...menuProps }"
                    icon="mdi-cog"
                    size="small"
                    variant="text"
                    @click.stop="specifyTag(item)"
                  />
                </template>

                <span>
                  Specify a run tag for this run to filter reports that
                  were <i>DETECTED</i> and <i>NOT FIXED BEFORE</i> the date
                  when the selected tag was created.
                </span>
              </v-tooltip>
            </template>

            <template v-slot:title="{ item }">
              <v-list-item-title :title="item.title">
                {{ item.title }}
              </v-list-item-title>
            </template>

            <template v-slot:icon>
              <v-icon color="grey">
                mdi-play-circle
              </v-icon>
            </template>
          </items>
        </template>

        <v-card
          v-if="selectTagForRun"
          flat
        >
          <baseline-tag-items
            :namespace="namespace"
            :selected-items="prevSelectedTagItems"
            :run-id="selectTagForRun.runIds[0]"
            :limit="defaultLimit"
            @apply="applyTagSelection"
            @cancel="cancelSelection"
            @select="selectRunTags"
          >
            <template v-slot:icon>
              <v-icon color="grey">
                mdi-tag
              </v-icon>
            </template>
          </baseline-tag-items>
        </v-card>
      </v-menu>
    </template>

    <template v-slot:default>
      <items-selected
        :selected-items="baseSelectOptionFilter.selectedItems.value"
        @update:select="updateSelectedItems"
      >
        <template v-slot:icon>
          <v-icon color="grey">
            mdi-play-circle
          </v-icon>
        </template>

        <template v-slot:title="{ item }">
          <v-list-item-title :title="titles[item.id]">
            {{ titles[item.id] }}
          </v-list-item-title>
        </template>
      </items-selected>
    </template>
  </select-option>
</template>

<script setup>
import { computed, ref, toRef } from "vue";
import { useRoute } from "vue-router";

import { ccService, extractTagWithRunName, handleThriftError } from "@cc-api";
import { ReportFilter } from "@cc/report-server-types";

import BulbMessage from "@/components/BulbMessage";
import {
  useBaseSelectOptionFilter
} from "@/composables/useBaseSelectOptionFilter";
import { useDateUtils } from "@/composables/useDateUtils";
import { useRunFilter } from "@/composables/useRunFilter";
import BaselineTagItems from "./BaselineTagItems";
import {
  Items,
  ItemsSelected,
  SelectOption,
  SelectedToolbarTitleItems,
  filterIsChanged
} from "./SelectOption";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([
  "update:url",
  "select"
]);

const baseSelectOptionFilter =
  useBaseSelectOptionFilter(toRef(props, "namespace"));
baseSelectOptionFilter.fetchItems.value = fetchItems;
baseSelectOptionFilter.updateReportFilter.value = updateReportFilter;

const id = "run";
baseSelectOptionFilter.id.value = id;

const runTagId = ref("run-tag");
const selectTagMenu = ref(false);
const selectTagForRun = ref(null);
const prevSelectedRuns = ref([]);
const prevSelectedTagItems = ref([]);
const search = ref({
  placeHolder: "Search for run names (e.g.: myrun*)...",
  regexLabel: "Filter by wildcard pattern (e.g.: myrun*)",
  filterItems: baseSelectOptionFilter.filterItems
});

const route = useRoute();
const runFilter = useRunFilter();
const { prettifyDate } = useDateUtils();

const titles = computed(() => {
  return baseSelectOptionFilter.selectedItems.value.reduce((acc, curr) => ({
    ...acc,
    [curr.id]: getSelectedRunTitle(curr).title
  }), {});
});

const selectedToolbarTitleItems = computed(() => {
  return (baseSelectOptionFilter.selectedItems.value || []).map(item => ({
    title: titles.value[item.id]
  }));
});

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function formatRunItemWithTags(run, tags) {
  const _tagNames = tags
    .filter(s => run.runIds.includes(s.runId))
    .map(s => s.tagName);

  run.title = _tagNames.length
    ? `${run.id}:${_tagNames.join(", ")}`
    : run.id;

  return run;
}

function formatRunTitle(run) {
  return formatRunItemWithTags(run, prevSelectedTagItems.value);
}

function getSelectedRunTitle(run) {
  return formatRunItemWithTags(run, runFilter.selectedTagItems.value);
}

function runFilterIsChanged(newSelection) {
  return filterIsChanged(
    prevSelectedRuns.value,
    newSelection
  );
}

/*function tagFilterIsChanged() {
  return filterIsChanged(
    prevSelectedTagItems.value,
    runFilter.selectedTagItems.value
  );
}*/

function updateSelectedItems(selectedRunItems) {
  setSelectedItems(selectedRunItems, runFilter.selectedTagItems.value);
}

function getSelectedRunItems(runNames) {
  return Promise.all(runNames.map(async s => ({
    id: s,
    runIds: await ccService.getRunIds(s),
    title: s,
    count: "N/A"
  })));
}

async function getSelectedTagItems(tags) {
  const _tagIds = [];
  const _tagWithRunNames = [];
  tags.forEach(t => {
    const _id = +t;
    if (isNaN(_id)) {
      _tagWithRunNames.push(t);
    } else {
      _tagIds.push(_id);
    }
  });

  // Get tags by tag ids.
  const _tags1 = _tagIds.length
    ? (await ccService.getTags(null, _tagIds)).map(t => {
      const time = prettifyDate(t.time);
      return {
        id: t.id.toNumber(),
        runName: t.runName,
        runId: t.runId.toNumber(),
        tagName : t.versionTag || time,
        time: time,
        title: t.versionTag,
        count: "N/A"
      };
    })
    : [];

  // Get tags by tag names (backward compatibility).
  const _tags2 = _tagWithRunNames.length
    ? (await Promise.all(_tagWithRunNames.map(async s => {
      const { runName, tagName } = extractTagWithRunName(s);
      const runIds = runName ? await ccService.getRunIds(runName) : null;
      const tags = await ccService.getTags(runIds, null, [ tagName ]);
      return {
        id: tags[0].id,
        runName: runName ? runName : tags[0].runName,
        runId: tags[0].runId.toNumber(),
        time: tags[0].time,
        tagName,
        title: s,
        count: "N/A"
      };
    })))
    : [];

  return _tags1.concat(_tags2);
}

async function initByUrl() {
  let _runs = [].concat(route.query[id] || []);
  const _tags = [].concat(route.query[runTagId.value] || []);

  if (_runs.length || _tags.length) {
    let _selectedTags = [];
    if (_tags.length) {
      _selectedTags = await getSelectedTagItems(_tags);

      // Add runs related to tags.
      _runs.push(..._selectedTags.map(t => t.runName));

      // Filter out duplicates.
      _runs = [ ...new Set(_runs) ];
    }

    const _selectedRuns = await getSelectedRunItems(_runs);
    prevSelectedRuns.value = _selectedRuns;
    prevSelectedTagItems.value = _selectedTags;

    await setSelectedItems(_selectedRuns, _selectedTags, false);
  }
}

function cancelSelection() {
  selectTagMenu.value = false;
  selectTagForRun.value = null;
}

function applySelection(selectedRunItems) {
  const isRunFilterChanged = runFilterIsChanged(selectedRunItems);
  if (!isRunFilterChanged) return;

  setSelectedItems(selectedRunItems, prevSelectedTagItems.value);
}

function applyTagSelection(selected) {
  prevSelectedTagItems.value = selected;
  selectTagMenu.value = false;
  prevSelectedTagItems.value.forEach(t => {
    emit("select", item => item.runIds.includes(t.runId));
  });
}

async function clear(updateUrl) {
  await setSelectedItems([], [], updateUrl);
}

function selectRunTags(selectedItems) {
  prevSelectedTagItems.value = selectedItems;
}

function getUrlState() {
  const _runState = baseSelectOptionFilter.selectedItems.value.map(
    item => baseSelectOptionFilter.encodeValue.value(item.id)
  );

  const _tagState = runFilter.selectedTagItems.value.map(item => item.id);

  return {
    [id]: _runState.length ? _runState : undefined,
    [runTagId.value]: _tagState.length ? _tagState : undefined
  };
}

async function setSelectedItems(runItems, tagItems, updateUrl=true) {
  baseSelectOptionFilter.selectedItems.value = runItems;

  // When removing a run with tag item from the selected filter list
  // we need to remove the tags too.
  runFilter.selectedTagItems.value = tagItems.filter(t =>
    runItems.findIndex(s => s.runIds.includes(t.runId)) > -1);
  prevSelectedRuns.value = runItems;
  prevSelectedTagItems.value = tagItems;

  await updateReportFilter();

  if (updateUrl) {
    emit("update:url");
  }
}

async function updateReportFilter() {
  const _selectedRunIds = await runFilter.getSelectedRunIds(
    baseSelectOptionFilter.selectedItems
  );
  baseSelectOptionFilter.setRunIds(
    _selectedRunIds.length ? _selectedRunIds : null
  );

  const _selectedTagIds = runFilter.selectedTagItems.value.map(t => t.id);
  baseSelectOptionFilter.reportFilter.value.runTag =
    _selectedTagIds.length ? _selectedTagIds : null;
}

function onRunIdsChange() {}

function onReportFilterChange(key) {
  if (key === "runName" || key === "runTag") return;
  baseSelectOptionFilter.update();
}

function fetchItems(opt={}) {
  baseSelectOptionFilter.loading.value = true;

  const _runIds = [];
  const _limit = opt.limit || baseSelectOptionFilter.defaultLimit.value;
  const _offset = 0;

  const _reportFilter = new ReportFilter(baseSelectOptionFilter.reportFilter);
  _reportFilter.runName = opt.query;
  _reportFilter.runTag = null;

  return new Promise((resolve, reject) => {
    ccService.getClient().getRunReportCounts(
      _runIds,
      _reportFilter,
      _limit,
      _offset,
      handleThriftError(res => {
        resolve(res.map(run => {
          return {
            id: run.name,
            runIds: [ run.runId.toNumber() ],
            title: run.name,
            count: run.reportCount.toNumber()
          };
        }));
        baseSelectOptionFilter.loading.value = false;
      }, err => {
        baseSelectOptionFilter.loading.value = false;
        reject(err);
      }));
  });
}

function specifyTag(run) {
  if (selectTagForRun.value === run) {
    selectTagForRun.value = null;
    return;
  }

  selectTagForRun.value = run;
  setTimeout(() => selectTagMenu.value = true, 0);
}

defineExpose({
  beforeInit: baseSelectOptionFilter.beforeInit,
  afterInit: baseSelectOptionFilter.afterInit,
  update: baseSelectOptionFilter.update,
  registerWatchers: baseSelectOptionFilter.registerWatchers,
  unregisterWatchers: baseSelectOptionFilter.unregisterWatchers,

  id,
  initByUrl,
  getUrlState,
  clear,
  updateReportFilter,
  onRunIdsChange,
  onReportFilterChange,
  fetchItems
}
);
</script>

<style lang="scss" scoped>
.v-tab {
  &.tags:not(.v-tab--disabled) {
    font-weight: bold;
  }

  &.v-tab--active:not(:focus)::before {
    opacity: 0.15;
  }
}
</style>
