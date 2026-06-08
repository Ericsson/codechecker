<template>
  <v-container>
    <h1>Manage Cleanup Plans</h1>
    <span
      class="subtitle-1"
    >
      Use cleanup plans to track progress of reports in your product.
    </span>

    <list-cleanup-plans />
  </v-container>
</template>

<script setup>
import {
  ListCleanupPlans
} from "@/components/Report/CleanupPlan";
</script>
