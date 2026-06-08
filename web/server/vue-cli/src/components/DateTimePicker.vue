<template>
  <v-dialog
    v-model="dialog"
    :content-class="dialogClass"
    width="400"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-text-field
        v-bind="activatorProps"
        v-model="formattedDateTime"
        :label="label"
        :class="[ inputClass, 'pa-0', 'ma-0' ]"
        :prepend-inner-icon="prependInnerIcon"
        :variant="variant"
        :density="density"
        hide-details
        readonly
      >
        <template #append-inner>
          <slot name="append-inner" />
        </template>
      </v-text-field>
    </template>

    <v-card>
      <v-card-text class="pa-0">
        <v-tabs
          v-model="activeTab"
          fixed-tabs
        >
          <v-tab>
            <v-icon>mdi-calendar</v-icon>
          </v-tab>

          <v-tab
            :disabled="!date"
          >
            <v-icon>mdi-clock-outline</v-icon>
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <v-window-item>
            <v-date-picker
              v-model="date"
              full-width
              @update:model-value="activeTab = 1"
            />
          </v-window-item>

          <v-window-item>
            <v-time-picker
              v-model="time"
              full-width
              use-seconds
              format="24hr"
            />
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="grey lighten-1"
          class="clear-btn"
          text
          @click="clear"
        >
          Clear
        </v-btn>

        <v-btn
          class="ok-btn"
          color="green darken-1"
          text
          @click="ok"
        >
          Ok
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {
  computed,
  onMounted,
  ref,
  watch
} from "vue";

const props = defineProps({
  modelValue: { type: [ Date, String ], default: null },
  label: { type: String, default: "" },
  dateFormat: { type: String, default: "yyyy-MM-dd" },
  timeFormat: { type: String, default: "HH:mm:ss" },
  defaultTime: { type: String, default: "00:00:00" },
  inputClass: { type: String, default: null },
  dialogClass: { type: String, default: null },
  variant: { type: String, default: "solo" },
  density: { type: String, default: "compact" },
  prependInnerIcon: { type: String, default: null },
});

const emit = defineEmits([
  "update:modelValue"
]);
import { format, parse } from "date-fns";
const dialog = ref(false);
const activeTab = ref(0);
const date = ref(null);
const time = ref(null);

const dateTimeFormat = computed(() =>
  `${props.dateFormat} ${props.timeFormat}`
);

const dateTime = computed(() => {
  if (date.value && time.value) {
    let dateStr;
    if (date.value instanceof Date) {
      dateStr = format(date.value, props.dateFormat);
    } else {
      dateStr = date.value;
    }
    
    const _dt = dateStr + " " + time.value;
    const _parsedDate = parse(_dt, dateTimeFormat.value, new Date());
    return !isNaN(_parsedDate) ? _parsedDate : null;
  }
  return null;
});

const formattedDateTime = computed(() => 
  dateTime.value &&
  !isNaN(dateTime.value) ? format(dateTime.value, dateTimeFormat.value) : null
);

watch(() => props.modelValue, init);

onMounted(() => {
  if (!time.value) {
    time.value = props.defaultTime;
  }
  init();
});

function init() {
  if (!props.modelValue) {
    resetDateTimes();
    return;
  }

  let initValue = null;
  if (props.modelValue instanceof Date) {
    initValue = props.modelValue;
  } else if (typeof props.modelValue === "string" ||
              props.modelValue instanceof String
  ) {
    initValue = parse(props.modelValue, dateTimeFormat.value, new Date());
  }

  // Check if initValue is a valid date
  if (!initValue || isNaN(initValue)) {
    resetDateTimes();
    return;
  }

  date.value = format(initValue, props.dateFormat);
  time.value = format(initValue, props.timeFormat);
}

function clear() {
  reset();
  resetDateTimes();

  emit("update:modelValue", null);
}

function ok() {
  emit("update:modelValue", dateTime.value);

  reset();
}

function reset() {
  dialog.value = false;
  activeTab.value = 0;
}

function resetDateTimes() {
  date.value = null;
  time.value = props.defaultTime;
}
</script>

<style lang="scss">
v-picker.v-card {
  box-shadow: none;

  & > .v-picker__title {
    border-radius: 0;
  }
}
</style>
