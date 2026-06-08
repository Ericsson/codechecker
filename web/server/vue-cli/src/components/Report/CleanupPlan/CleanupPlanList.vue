<template>
  <v-list
    v-if="cleanupPlans && cleanupPlans.length"
    v-model:selected="internalSelectedPlans"
    select-strategy="multiple"
  >
    <v-list-item
      v-for="cleanupPlan in cleanupPlans"
      :key="cleanupPlan.id.toNumber()"
      :value="cleanupPlan.id.toNumber()"
    >
      <template v-slot:prepend="{ isActive }">
        <v-icon v-if="isActive">
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
  cleanupPlans: { type: Array, default: null },
  selectedPlans: { type: Array, default: () => [] },
  notAllSelected: { type: Object, default: () => ({}) }
});

const emit = defineEmits([ "update:selectedPlans" ]);

const internalSelectedPlans = computed({
  get() {
    return props.selectedPlans;
  },
  set(value) {
    emit("update:selectedPlans", value);
  }
});
</script>
