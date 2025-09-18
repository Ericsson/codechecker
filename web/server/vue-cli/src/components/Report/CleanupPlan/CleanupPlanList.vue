<template>
  <v-list v-if="value && value.length">
    <template v-for="(cleanupPlan, idx) in value" :key="cleanupPlan.id.toNumber()">
      <v-list-item
        :value="cleanupPlan.id.toNumber()"
      >
        <template v-slot:default="{ active }">
          <v-list-item-action class="ma-1 mr-5">
            <v-icon v-if="active">
              mdi-check
            </v-icon>

            <v-icon v-else-if="notAllSelected[cleanupPlan.id]">
              mdi-minus
            </v-icon>
          </v-list-item-action>

          <v-list-item-content class="py-1">
            <v-list-item-title class="font-weight-bold">
              {{ cleanupPlan.name }}
            </v-list-item-title>

            <v-list-item-subtitle
              v-if="cleanupPlan.closedAt"
            >
              <v-icon small>
                mdi-calendar-blank
              </v-icon>
              Closed on
              {{ cleanupPlan.closedAt | fromUnixTime("yyyy-MM-dd") }}
            </v-list-item-subtitle>

            <v-list-item-subtitle
              v-else-if="cleanupPlan.dueDate"
            >
              <due-date :value="cleanupPlan.dueDate" />
            </v-list-item-subtitle>

            <v-list-item-subtitle v-else>
              No due date
            </v-list-item-subtitle>
          </v-list-item-content>
        </template>
      </v-list-item>

      <v-divider
        v-if="idx < value.length - 1"
        :key="`divider-${idx}`"
      />
    </template>
  </v-list>

  <v-list v-else disabled>
    <v-list-item>
      No cleanup plan.
    </v-list-item>
  </v-list>
</template>

<script>
import DueDate from "./DueDate";

export default {
  name: "CleanupPlanList",
  components: {
    DueDate
  },
  props: {
    value: { type: Array, default: null },
    notAllSelected: { type: Object, default: () => ({}) }
  },
};
</script>
