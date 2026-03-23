<template>
  <v-menu
    v-model="menu"
    :close-on-content-click="false"
    :nudge-right="40"
    transition="scale-transition"
    offset-y
    min-width="auto"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-text-field
        v-bind="activatorProps"
        :value="date"
        label="Due date"
        append-icon="mdi-calendar"
        readonly
        variant="outlined"
      />
    </template>

    <v-date-picker v-model="date" />
  </v-menu>
</template>

<script setup>
import { format, fromUnixTime, getUnixTime, parse } from "date-fns";
import { computed, ref } from "vue";

const props = defineProps({
  value: { type: Number, default: null },
});

const emit = defineEmits([ "update:value" ]);

const menu = ref(false);
const dateFormatStr = "yyyy-MM-dd";

const date = computed({
  get() {
    return format(fromUnixTime(props.value), dateFormatStr, new Date);
  },
  set(val) {
    emit("update:value", getUnixTime(parse(val, dateFormatStr, new Date)));
    menu.value = false;
  },
});
</script>
