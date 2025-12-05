<template>
  <v-list
    v-if="value && value.length"
    v-model:selected="selected"
    select-strategy="multiple"
  >
    <template 
      v-for="(cleanupPlan, idx) in value"
      :key="cleanupPlan.id.toNumber()"
    >
      <v-list-item
        :value="cleanupPlan.id.toNumber()"
      >
        <template v-slot:prepend="{ isSelected }">
          <v-icon v-if="isSelected">
            mdi-checkbox-marked
          </v-icon>
          <v-icon v-else-if="notAllSelected[cleanupPlan.id]">
            mdi-checkbox-intermediate
          </v-icon>
          <v-icon v-else>
            mdi-checkbox-blank-outline
          </v-icon>
        </template>

        <v-list-item-title class="font-weight-bold">
          {{ cleanupPlan.name }}
        </v-list-item-title>

        <v-list-item-subtitle
          v-if="cleanupPlan.closedAt"
        >
          <v-icon
            size="small"
          >
            mdi-calendar-blank
          </v-icon>
          Closed on
          {{ fromUnixTime(cleanupPlan.closedAt, "yyyy-MM-dd") }}
        </v-list-item-subtitle>

        <v-list-item-subtitle
          v-else-if="cleanupPlan.dueDate"
        >
          <due-date :value="cleanupPlan.dueDate" />
        </v-list-item-subtitle>

        <v-list-item-subtitle
          v-else
        >
          No due date
        </v-list-item-subtitle>
      </v-list-item>

      <v-divider
        v-if="idx < value.length - 1"
        :key="idx"
      />
    </template>
  </v-list>

  <v-list v-else disabled>
    <v-list-item>
      No cleanup plan.
    </v-list-item>
  </v-list>
</template>

<script setup>
import { computed } from "vue";
import DueDate from "./DueDate";

const props = defineProps({
  value: { type: Array, default: null },
  selectedItems: { type: Array, default: () => [] },
  notAllSelected: { type: Object, default: () => ({}) }
});

const emit = defineEmits([ "update:selected-items" ]);

const selected = computed({
  get: () => props.selectedItems,
  set: val => emit("update:selected-items", val)
});
</script>
