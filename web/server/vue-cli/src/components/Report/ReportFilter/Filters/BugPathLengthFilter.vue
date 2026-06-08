<template>
  <filter-toolbar
    title="Bug path length"
    :panel="panel"
    @clear="clear(true)"
  >
    <template v-slot:append-toolbar-title>
      <span
        v-if="selectedBugPathLengthTitle"
        class="selected-items"
        :title="selectedBugPathLengthTitle"
      >
        ({{ selectedBugPathLengthTitle }})
      </span>
    </template>

    <v-form ref="form">
      <v-container
        class="py-0"
      >
        <v-row>
          <v-col
            cols="12"
            sm="6"
            md="6"
            class="py-0"
          >
            <v-text-field
              :id="minId"
              :value="minBugPathLength"
              :rules="rules.bugPathLength"
              label="Min..."
              @input="setMinBugPathLength"
            />
          </v-col>

          <v-col
            cols="12"
            sm="6"
            md="6"
            class="py-0"
          >
            <v-text-field
              :id="maxId"
              :value="maxBugPathLength"
              :rules="rules.bugPathLength"
              label="Max..."
              @input="setMaxBugPathLength"
            />
          </v-col>
        </v-row>
      </v-container>
    </v-form>
  </filter-toolbar>
</template>

<script setup>
import { BugPathLengthRange } from "@cc/report-server-types";
import { computed, ref, toRef } from "vue";

import { useBaseFilter } from "@/composables/useBaseFilter";
import FilterToolbar from "./Layout/FilterToolbar";

import { useRoute } from "vue-router";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([
  "update:url"
]);

const baseFilter = useBaseFilter(toRef(props, "namespace"));

const { panel, setReportFilter } = baseFilter;

const minId = ref("min-bug-path-length");
const maxId = ref("max-bug-path-length");
const minBugPathLength = ref(null);
const maxBugPathLength = ref(null);
const rules = ref({
  bugPathLength: [
    v => (!v || !!v && !isNaN(parseInt(v))) || "Number is required"
  ]
});
const form = ref(null);

const route = useRoute();

const selectedBugPathLengthTitle = computed(() => {
  return [
    ...(minBugPathLength.value ? [ `min: ${minBugPathLength.value}` ] : []),
    ...(maxBugPathLength.value ? [ `max: ${maxBugPathLength.value}` ] : [])
  ].join(", ");
});

function setMinBugPathLength(_bugPathLength, _updateUrl=true) {
  if (form.value && !form.value.validate()) return;

  minBugPathLength.value = _bugPathLength;
  updateReportFilter();

  if (_updateUrl) {
    emit("update:url");
  }
}

function setMaxBugPathLength(_bugPathLength, _updateUrl=true) {
  if (form.value && !form.value.validate()) return;

  maxBugPathLength.value = _bugPathLength;
  updateReportFilter();

  if (_updateUrl) {
    emit("update:url");
  }
}

function getUrlState() {
  return {
    [minId.value]: minBugPathLength.value || undefined,
    [maxId.value]: maxBugPathLength.value || undefined
  };
}

function initByUrl() {
  return new Promise(resolve => {
    const _minBugPathLength = route.query[minId.value];
    if (parseInt(_minBugPathLength)) {
      setMinBugPathLength(_minBugPathLength, false);
    }

    const _maxBugPathLength = route.query[maxId.value];
    if (parseInt(_maxBugPathLength)) {
      setMaxBugPathLength(_maxBugPathLength, false);
    }

    resolve();
  });
}

function initPanel() {
  panel.value = minBugPathLength.value !== null ||
    maxBugPathLength.value !== null;
}

function updateReportFilter() {
  let _bugPathLength = null;

  if (minBugPathLength.value || maxBugPathLength.value)  {
    _bugPathLength = new BugPathLengthRange({
      min : minBugPathLength.value ? minBugPathLength.value : null,
      max : maxBugPathLength.value ? maxBugPathLength.value : null,
    });
  }

  setReportFilter({ bugPathLength: _bugPathLength });
}

function clear(updateUrl) {
  setMinBugPathLength(null, false);
  setMaxBugPathLength(null, false);

  if (updateUrl) {
    emit("update:url");
  }
}

defineExpose({
  beforeInit: baseFilter.beforeInit,
  afterInit: baseFilter.afterInit,
  registerWatchers: baseFilter.registerWatchers,
  unregisterWatchers: baseFilter.unregisterWatchers,

  getUrlState,
  initByUrl,
  initPanel,
  clear,
  updateReportFilter,
});
</script>
