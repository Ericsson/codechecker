<template>
  <v-container>
    <v-tabs v-model="tab">
      <v-tab
        v-for="item in [ 'Open', 'Closed' ]"
        :key="item"
        class="font-weight-bold subtitle-2 text-capitalize"
      >
        {{ item }}
      </v-tab>
    </v-tabs>

    <v-window v-model="tab">
      <v-window-item>
        <slot name="open" />
      </v-window-item>

      <v-window-item>
        <slot name="closed" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  modelValue: { type: Number, default: 0 }
});

const emit = defineEmits([ "update:modelValue" ]);

const tab = computed({
  get: () => props.modelValue,
  set: pos => emit("update:modelValue", pos)
});
</script>
