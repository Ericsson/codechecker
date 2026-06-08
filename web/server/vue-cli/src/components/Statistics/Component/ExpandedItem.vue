<template>
  <td class="pa-0" :colspan="colspan">
    <v-card flat tile>
      <v-card-text
        v-if="item.loading || !item.checkerStatistics"
      >
        Loading...
        <v-progress-linear
          indeterminate
          class="mb-0"
        />
      </v-card-text>

      <checker-statistics-table
        v-else
        :items="item.checkerStatistics"
        :loading="item.loading"
      />
    </v-card>
  </td>
</template>

<script>
import { CheckerStatisticsTable } from "@/components/Statistics";

export default {
  name: "ExpandedItem",
  components: { CheckerStatisticsTable },
  props: {
    item: { type: Object, required: true },
    colspan: { type: Number, required: true }
  }
};
</script>
