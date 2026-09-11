<template>
  <v-toolbar
    flat
    class="mb-4 run-filter-toolbar"
    color="transparent"
  >
    <div class="d-flex align-center w-100 search-row">
      <div class="d-flex align-center search-group">
        <v-text-field
          v-model="runName"
          class="run-name flex-grow-1"
          prepend-inner-icon="mdi-magnify"
          label="Search for runs..."
          single-line
          hide-details
          clearable
          variant="outlined"
          density="compact"
        />

        <v-btn
          class="toggle-filters-btn ml-2 px-4"
          variant="tonal"
          height="40"
          :color="showFilters ? 'primary' : undefined"
          @click="showFilters = !showFilters"
        >
          <v-icon right>
            mdi-filter-variant
          </v-icon>
          <v-icon right>
            {{ showFilters ? "mdi-chevron-up" : "mdi-chevron-down" }}
          </v-icon>
        </v-btn>
      </div>

      <LoadMultipleRunsBtn
        class="ml-2"
        :selected="selected"
        :disabled="!enoughRunsSelected"
        :report-filter-query="getSelectedRunsFilterQuery(props.selected)"
      />
      <DeleteRunBtn
        :selected="selected"
        variant="tonal"
        @on-confirm="update"
        @delete-complete="emit('delete-complete')"
      />
      <v-btn
        class="diff-runs-btn ml-2 px-4"
        variant="tonal"
        color="primary"
        height="40"
        :to="diffTargetRoute"
        :disabled="isDiffBtnDisabled"
      >
        <v-icon left>
          mdi-select-compare
        </v-icon>
        Diff
        <tooltip-help-icon>
          Compare the set of <i>outstanding reports</i> in two run (or tag)
          sets.<br>
          A report is outstanding if <b> all of the following is true</b>:
          <ul>
            <li>
              its detection status is <i>new</i>, <i>reopened</i>, or
              <i>unresolved</i>,
            </li>
            <li>
              its review status is <i>unreviewed</i> or <i>confirmed</i>.
            </li>
          </ul>
        </tooltip-help-icon>
      </v-btn>

      <v-spacer />

      <v-btn
        icon
        class="reload-runs-btn"
        title="Reload runs"
        color="primary"
        @click="update"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
    </div>

    <v-expand-transition>
      <v-row v-show="showFilters" class="additional-filters" no-gutters>
        <v-col cols="auto" align-self="center">
          <v-text-field
            v-model="runTag"
            class="run-tag additional-filter-input"
            prepend-inner-icon="mdi-tag"
            label="Filter events by tag name..."
            clearable
            single-line
            hide-details
            variant="outlined"
            density="compact"
          >
            <template #append-inner>
              <tooltip-help-icon>
                Filter run history events by the given tag name.<br>
                <i>Note</i>: this will filter only the history events.
              </tooltip-help-icon>
            </template>
          </v-text-field>
        </v-col>

        <v-col cols="auto" align-self="center">
          <DateTimePicker
            v-model="storedAfter"
            input-class="stored-after additional-filter-input"
            dialog-class="stored-after"
            label="History stored after..."
            prepend-inner-icon="mdi-calendar-arrow-right"
            variant="outlined"
            density="compact"
            clearable
          >
            <template #append-inner>
              <tooltip-help-icon>
                Filter run history events that were stored after the given
                date.<br>
                <i>Note</i>: this will filter only the history events.
              </tooltip-help-icon>
            </template>
          </DateTimePicker>
        </v-col>

        <v-col cols="auto" align-self="center">
          <DateTimePicker
            v-model="storedBefore"
            input-class="stored-before additional-filter-input"
            dialog-class="stored-before"
            label="History stored before..."
            prepend-inner-icon="mdi-calendar-arrow-left"
            variant="outlined"
            density="compact"
            clearable
          >
            <template #append-inner>
              <tooltip-help-icon>
                Filter run history events that were stored before the given
                date.<br>
                <i>Note</i>: this will filter only the history events.
              </tooltip-help-icon>
            </template>
          </DateTimePicker>
        </v-col>
      </v-row>
    </v-expand-transition>
  </v-toolbar>
</template>

<script setup>
import {
  computed,
  onMounted,
  ref,
  watch
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";

import { useDateUtils } from "@/composables/useDateUtils";

import {
  SET_RUN_HISTORY_RUN_TAG,
  SET_RUN_HISTORY_STORED_AFTER,
  SET_RUN_HISTORY_STORED_BEFORE,
  SET_RUN_NAME
} from "@/store/mutations.type";
import _ from "lodash";

import DateTimePicker from "@/components/DateTimePicker";
import { DeleteRunBtn, LoadMultipleRunsBtn } from "@/components/Run";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";

const props = defineProps({
  selected: { type: Array, required: true },
  selectedBaselineRuns: { type: Array, required: true },
  selectedBaselineTags: { type: Array, required: true },
  selectedComparedToRuns: { type: Array, required: true },
  selectedComparedToTags: { type: Array, required: true }
});
const emit = defineEmits([
  "on-run-filter-changed",
  "on-run-history-filter-changed",
  "update",
  "delete-complete"
]);
const route = useRoute();
const router = useRouter();
const store = useStore();

const showFilters = ref(
  Boolean(
    route.query["run-tag"] ||
    route.query["stored-after"] ||
    route.query["stored-before"]
  )
);

const { dateTimeToStr } = useDateUtils();

const setRunName = value => store.commit(
  `run/${SET_RUN_NAME}`, value
);
const setRunTag = value => store.commit(
  `run/${SET_RUN_HISTORY_RUN_TAG}`, value
);
const setStoredBefore = value => store.commit(
  `run/${SET_RUN_HISTORY_STORED_BEFORE}`, value
);
const setStoredAfter = value => store.commit(
  `run/${SET_RUN_HISTORY_STORED_AFTER}`, value
);

watch(() => store.getters["run/runName"], _.debounce(_runName => {
  const value = _runName ? _runName : undefined;
  updateUrl({ "run": value });
  emit("on-run-filter-changed");
}, 500));

watch(() => store.getters["run/runTag"], _.debounce(_runTag => {
  const value = _runTag ? _runTag : undefined;
  updateUrl({ "run-tag": value });
  emit("on-run-history-filter-changed");
}, 500));

watch(() => store.getters["run/storedAfter"], _.debounce(_storedAfter => {
  let _date = _storedAfter;
  if (_date instanceof Date) {
    _date = dateTimeToStr(_date);
  }

  updateUrl({ "stored-after": _date || undefined });
  emit("on-run-filter-changed");
  emit("on-run-history-filter-changed");
}, 500));

watch(() => store.getters["run/storedBefore"], _.debounce(_storedBefore => {
  let _date = _storedBefore;
  if (_date instanceof Date) {
    _date = dateTimeToStr(_date);
  }
  updateUrl({ "stored-before": _date || undefined });
  emit("on-run-filter-changed");
  emit("on-run-history-filter-changed");
}, 500));

const runName = computed({
  get: () => store.getters["run/runName"],
  set: value => setRunName(value)
});

const runTag = computed({
  get: () => store.getters["run/runTag"],
  set: value => setRunTag(value)
});

const storedBefore = computed({
  get: () => store.getters["run/storedBefore"],
  set: value => setStoredBefore(value)
});

const storedAfter = computed({
  get: () => store.getters["run/storedAfter"],
  set: value => setStoredAfter(value)
});

const isDiffBtnDisabled = computed(() => {
  return (!props.selectedBaselineRuns.length &&
          !props.selectedBaselineTags.length) ||
         (!props.selectedComparedToRuns.length &&
          !props.selectedComparedToTags.length);
});

const diffTargetRoute = computed(() => {
  return {
    name: "reports",
    query: {
      ...route.query,
      "run": props.selectedBaselineRuns.length
        ? props.selectedBaselineRuns : undefined,
      "run-tag": props.selectedBaselineTags.length
        ? props.selectedBaselineTags : undefined,
      "newcheck": props.selectedComparedToRuns.length
        ? props.selectedComparedToRuns : undefined,
      "run-tag-newcheck": props.selectedComparedToTags.length
        ? props.selectedComparedToTags : undefined,
      "diff-type": "New"
    }
  };
});

onMounted(() => {
  initByUrl();
});

function initByUrl() {
  const runName = route.query["run"];
  if (runName)
    setRunName(runName);

  const runTag = route.query["run-tag"];
  if (runTag)
    setRunTag(runTag);

  const storedAfter = route.query["stored-after"];
  if (storedAfter) {
    const date = new Date(storedAfter);
    if (!isNaN(date)) setStoredAfter(date);
  }

  const storedBefore = route.query["stored-before"];
  if (storedBefore) {
    const date = new Date(storedBefore);
    if (!isNaN(date)) setStoredBefore(date);
  }
}

function updateUrl(params) {
  router.replace({
    query: {
      ...route.query,
      ...params
    }
  }).catch(() => {});
}

function update() {
  emit("update");
}

function getSelectedRunsFilterQuery(selected) {
  return {
    run: selected.map(item => item.name)
  };
}

const enoughRunsSelected = computed(() => {
  return props.selected.length >= 1;
});

</script>

<style lang="scss" scoped>
.run-filter-toolbar :deep(.v-toolbar__content) {
  height: auto !important;
  flex-direction: column;
  align-items: stretch;
}

$filter-input-width: 260px;
$filter-gap: 16px;

.additional-filters {
  gap: $filter-gap;
}

.additional-filters > .v-col {
  width: $filter-input-width;
  flex: 0 0 $filter-input-width;
}

.search-group {
  width: ($filter-input-width * 3) + ($filter-gap * 2);
  max-width: 100%;
}
</style>
