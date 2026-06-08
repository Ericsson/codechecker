<template>
  <filter-toolbar
    :id="id"
    title="Outstanding reports on a given date"
    :panel="baseFilter.panel"
    @clear="clear(true)"
  >
    <template v-slot:append-toolbar-title>
      <tooltip-help-icon
        class="mr-2"
      >
        Filter reports that were <i>DETECTED BEFORE</i> the given date and
        <i>NOT FIXED BEFORE</i> the given date.<br><br>

        The <i>detection date</i> of a report is the <i>storage date</i> when
        the report was stored to the server for the first time and the
        <i>fix date</i> is the date when the report is <i>dissappeared</i>
        from a storage.
      </tooltip-help-icon>

      <span
        v-if="selectedDateTitle"
        class="selected-items"
        :title="selectedDateTitle"
      >
        ({{ selectedDateTitle }})
      </span>
    </template>

    <v-card-actions>
      <date-time-picker
        :input-class="id"
        :dialog-class="id"
        :model-value="date"
        variant="underlined"
        label="Report date"
        @update:model-value="setDateTime"
      />
    </v-card-actions>
  </filter-toolbar>
</template>

<script setup>
import { computed, ref, toRef } from "vue";

import { useRoute } from "vue-router";

import DateTimePicker from "@/components/DateTimePicker";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { useBaseFilter } from "@/composables/useBaseFilter";
import { useDateUtils } from "@/composables/useDateUtils";

import FilterToolbar from "./Layout/FilterToolbar";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([
  "update:url"
]);

const id = ref("open-reports-date");
const date = ref(null);

const { dateTimeToStr, getUnixTime } = useDateUtils();

const baseFilter = useBaseFilter(toRef(props, "namespace"));

const route = useRoute();

const selectedDateTitle = computed(() => 
  date.value ? dateTimeToStr(date.value) : null
);

function setDateTime(_date, updateUrl=true) {
  date.value = _date;
  updateReportFilter();

  if (updateUrl) {
    emit("update:url");
  }
}

function updateReportFilter() {
  baseFilter.setReportFilter({
    openReportsDate: date.value ? getUnixTime(date.value) : null
  });
}

function getUrlState() {
  return {
    [ id.value ]: date.value ? dateTimeToStr(date.value) : undefined
  };
}

function initByUrl() {
  const _date = route.query[id.value];
  if (_date) {
    const _dateTime = new Date(_date);

    // We need to round the date upward because we will send the dates
    // to the server without milliseconds.
    if (_dateTime.getMilliseconds()) {
      _dateTime.setMilliseconds(1000);
    }

    setDateTime(_dateTime, false);
  }
}

function initPanel() {
  baseFilter.panel.value = date.value !== null;
}

function clear(updateUrl) {
  setDateTime(null, updateUrl);
}

defineExpose({
  beforeInit: baseFilter.beforeInit,
  afterInit: baseFilter.afterInit,
  registerWatchers: baseFilter.registerWatchers,
  unregisterWatchers: baseFilter.unregisterWatchers,

  id,
  updateReportFilter,
  getUrlState,
  initByUrl,
  initPanel,
  clear
});
</script>
