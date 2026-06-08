<template>
  <select-option
    :title="title"
    :bus="baseSelectOptionFilter.bus"
    :fetch-items="fetchItems"
    :selected-items="baseSelectOptionFilter.selectedItems.value"
    :loading="baseSelectOptionFilter.loading.value"
    :multiple="false"
    :panel="baseSelectOptionFilter.panel.value"
    @clear="clear(true)"
    @input="setSelectedItems"
  >
    <template v-slot:icon="{ item }">
      <detection-date-filter-icon :value="item.id" />
    </template>

    <template v-slot:append-toolbar-title>
      <span
        v-if="selectedDetectionDateTitle"
        class="selected-items"
        :title="selectedDetectionDateTitle"
      >
        ({{ selectedDetectionDateTitle }})
      </span>
    </template>

    <v-container
      class="py-0"
    >
      <v-row>
        <v-col
          cols="12"
          sm="6"
          md="6"
        >
          <date-time-picker
            :input-class="fromDateTimeId"
            :dialog-class="fromDateTimeId"
            :model-value="fromDateTime"
            :label="fromDateTimeLabel"
            variant="underlined"
            @update:model-value="setFromDateTime"
          />
        </v-col>

        <v-col
          cols="12"
          sm="6"
          md="6"
        >
          <date-time-picker
            :input-class="toDateTimeId"
            :dialog-class="toDateTimeId"
            :model-value="toDateTime"
            :label="toDateTimeLabel"
            variant="underlined"
            @update:model-value="setToDateTime"
          />
        </v-col>
      </v-row>
    </v-container>
  </select-option>
</template>

<script setup>
import { DateInterval, ReportDate } from "@cc/report-server-types";
import { computed, ref, toRef } from "vue";

import { useRoute } from "vue-router";

import DateTimePicker from "@/components/DateTimePicker";
import {
  useBaseSelectOptionFilter
} from "@/composables/useBaseSelectOptionFilter";
import { useDateUtils } from "@/composables/useDateUtils";
import DetectionDateFilterIcon from "./DetectionDateFilterIcon";
import DetectionDateFilterItems, {
  getDateInterval,
  titleFormatter
} from "./DetectionDateFilterItems";
import SelectOption from "./SelectOption/SelectOption";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([
  "update:url"
]);

const baseSelectOptionFilter =
  useBaseSelectOptionFilter(toRef(props, "namespace"));
baseSelectOptionFilter.fetchItems.value = fetchItems;
baseSelectOptionFilter.updateReportFilter.value = updateReportFilter;

const { dateTimeToStr, getUnixTime } = useDateUtils();

const title = "Fix date";
const fromDateTimeId = "fixed-after";
const toDateTimeId = "fixed-before";
const fromDateTimeLabel = "Fixed after...";
const toDateTimeLabel = "Fixed before...";
const fromDateTime = ref(null);
const toDateTime = ref(null);
const filterFieldName = "fixed";

const route = useRoute();

const selectedDetectionDateTitle = computed(() => {
  return [
    ...(fromDateTime.value
      ? [ `after: ${dateTimeToStr(fromDateTime.value)}` ] : []),
    ...(toDateTime.value
      ? [ `before: ${dateTimeToStr(toDateTime.value)}` ] : [])
  ].join(", ");
});

baseSelectOptionFilter.bus.on("update:url", () => {
  emit("update:url");
});

function setSelectedItems(_selectedItems/*, updateUrl=true*/) {
  baseSelectOptionFilter.selectedItems.value = _selectedItems;
  const _interval = getDateInterval(
    baseSelectOptionFilter.selectedItems.value.id
  );

  setFromDateTime(_interval.from, false);
  setToDateTime(_interval.to, false);

  emit("update:url");
}

function setFromDateTime(_dateTime, _updateUrl=true) {
  fromDateTime.value = _dateTime;
  updateReportFilter();

  if (_updateUrl) {
    baseSelectOptionFilter.selectedItems.value = [];
    emit("update:url");
  }
}

function setToDateTime(_dateTime, _updateUrl=true) {
  toDateTime.value = _dateTime;
  updateReportFilter();

  if (_updateUrl) {
    baseSelectOptionFilter.selectedItems.value = [];
    emit("update:url");
  }
}

function getUrlState() {
  const _state = {};

  _state[fromDateTimeId] = fromDateTime.value
    ? dateTimeToStr(fromDateTime.value) : undefined;

  _state[toDateTimeId] = toDateTime.value
    ? dateTimeToStr(toDateTime.value) : undefined;

  return _state;
}

function initByUrl() {
  return new Promise(resolve => {
    const _fromDateTime = route.query[fromDateTimeId];
    if (_fromDateTime) {
      setFromDateTime(new Date(_fromDateTime), false);
    }

    const _toDateTime = route.query[toDateTimeId];
    if (_toDateTime) {
      const _dateTime = new Date(_toDateTime);

      // We need to round the date upward because we will send the dates
      // to the server without milliseconds.
      if (_dateTime.getMilliseconds()) {
        _dateTime.setMilliseconds(1000);
      }

      setToDateTime(_dateTime, false);
    }

    resolve();
  });
}

function initPanel() {
  baseSelectOptionFilter.panel.value =
    fromDateTime.value !== null || toDateTime.value !== null;
}

function updateReportFilter() {
  const _date = new ReportDate(
    baseSelectOptionFilter.reportFilter.value.date
  );
  if (fromDateTime.value || toDateTime.value) {
    if (!_date[filterFieldName])
      _date[filterFieldName] = new DateInterval();

    _date[filterFieldName].before = toDateTime.value
      ? getUnixTime(toDateTime.value) : null;
    _date[filterFieldName].after = fromDateTime.value
      ? getUnixTime(fromDateTime.value) : null;
  } else if (_date) {
    _date[filterFieldName] = null;
  }

  baseSelectOptionFilter.setReportFilter({ date: _date });
}

function fetchItems() {
  return Object.keys(DetectionDateFilterItems).map(key => {
    const _id = DetectionDateFilterItems[key];

    return {
      id: _id,
      title: titleFormatter(_id)
    };
  });
}

function clear(updateUrl) {
  setFromDateTime(null, false);
  setToDateTime(null, false);
  baseSelectOptionFilter.selectedItems.value = [];

  if (updateUrl) {
    emit("update:url");
  }
}

defineExpose({
  beforeInit: baseSelectOptionFilter.beforeInit,
  afterInit: baseSelectOptionFilter.afterInit,
  update: baseSelectOptionFilter.update,
  registerWatchers: baseSelectOptionFilter.registerWatchers,
  unregisterWatchers: baseSelectOptionFilter.unregisterWatchers,

  setSelectedItems,
  getUrlState,
  initByUrl,
  initPanel,
  clear,
  updateReportFilter,
  fetchItems
}
);
</script>

