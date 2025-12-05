<template>
  <v-checkbox
    v-model="isUniqueModel"
    :hide-details="true"
  >
    <template v-slot:label>
      Unique reports
      <tooltip-help-icon
        class="mr-2"
      >
        This narrows the report list to unique report types. The same bug may
        appear several times if it is found in different runs or on different
        control paths, i.e. through different function calls. By checking
        <b>Unique reports</b>, a report appears only once even if it is found
        on several paths or in different runs.
      </tooltip-help-icon>
    </template>
  </v-checkbox>
</template>

<script setup>
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { useBaseFilter } from "@/composables/useBaseFilter";
import { ref, toRef, watch } from "vue";
import { useRoute } from "vue-router";

const props = defineProps({
  namespace: { type: String, required: true }
});

const emit = defineEmits([ "update:url" ]);
const id = ref("is-unique");
const defaultValue = ref(false);
const isUniqueModel = ref(false);

const baseFilter = useBaseFilter(toRef(props, "namespace"));

const route = useRoute();

watch(isUniqueModel, value => {
  setIsUnique(value);
});

function setIsUnique(val, updateUrl=true) {
  baseFilter.setReportFilter({ isUnique: val });
  if (updateUrl) {
    emit("update:url");
  }
}

function encodeValue(boolVal) {
  return boolVal ? "on" : "off";
}

function decodeValue(stateVal) {
  return stateVal === "on" ? true : false;
}

function getUrlState() {
  return {
    [id.value]: encodeValue(isUniqueModel.value)
  };
}

function initByUrl() {
  return new Promise(resolve => {
    const _state = route.query[id.value];
    isUniqueModel.value = decodeValue(_state);

    resolve();
  });
}

function clear(updateUrl) {
  setIsUnique(defaultValue.value, updateUrl);
}

defineExpose({
  beforeInit: baseFilter.beforeInit,
  afterInit: baseFilter.afterInit,
  registerWatchers: baseFilter.registerWatchers,
  unregisterWatchers: baseFilter.unregisterWatchers,

  id,
  encodeValue,
  decodeValue,
  getUrlState,
  initByUrl,
  clear
});
</script>
