<template>
  <v-menu
    v-model="menuOpen"
    :close-on-content-click="false"
    :nudge-right="40"
    transition="scale-transition"
    offset-y
    min-width="auto"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-text-field
        v-bind="activatorProps"
        v-model="date"
        label="Due date"
        append-inner-icon="mdi-calendar"
        readonly
        variant="outlined"
      />
    </template>

    <v-date-picker v-model="date" />
  </v-menu>
</template>

<script setup>
import { format, fromUnixTime, getUnixTime } from "date-fns";
import { computed, ref } from "vue";

const props = defineProps({
  modelValue: { type: Number, default: null },
});

const emit = defineEmits([ "update:modelValue" ]);

const menuOpen = ref(false);
const dateFormatStr = "yyyy-MM-dd";

const date = computed({
  get() {
    return props.modelValue ?
      format(fromUnixTime(props.modelValue), dateFormatStr) : null;
  },
  set(val) {
    emit("update:modelValue", getUnixTime(val));
    menuOpen.value = false;
  },
});
</script>
