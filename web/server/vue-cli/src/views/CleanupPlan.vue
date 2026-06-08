<template>
  <v-container>
    <h1>Manage Cleanup Plans</h1>
    <cleanup-plan-subtitle />

    <list-cleanup-plans />
  </v-container>
</template>

<script>
import {
  CleanupPlanSubtitle,
  ListCleanupPlans
} from "@/components/Report/CleanupPlan";

export default {
  name: "CleanupPlan",
  components: { CleanupPlanSubtitle, ListCleanupPlans }
};
</script>
