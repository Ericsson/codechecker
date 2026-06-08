<template>
  <v-container fluid>
    <h1>Manage review status rules</h1>
    <span
      class="subtitle-1"
    >
      Sets the review status of all reports without source code comment even
      in the future. We don't recommend setting review status for reports which
      already have one as a source code comment!
    </span>
    <list-review-status-rules />
  </v-container>
</template>

<script setup>
import { ListReviewStatusRules } from "@/components/ReviewStatus";
</script>
