<template>
  <v-container fluid>
    <h1>Manage review status rules</h1>
    <div class="subtitle-1">
      Sets the review status of all reports without source code comment even
      in the future. We don't recommend setting review status for reports which
      already have one as a source code comment!
    </div>
    <list-review-status-rules />
  </v-container>
</template>

<script>
import { ListReviewStatusRules } from "@/components/ReviewStatus";

export default {
  name: "ReviewStatusRules",
  components: { ListReviewStatusRules }
};
</script>
