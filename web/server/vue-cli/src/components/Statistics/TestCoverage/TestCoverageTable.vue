<template>
  <div class="test-coverage-table w-100">
    <v-row class="ma-0 mb-2" align="center">
      <v-breadcrumbs
        :items="breadcrumbs"
        class="pa-0 flex-grow-1 coverage-breadcrumbs"
        aria-label="Current directory"
      >
        <template v-slot:divider>
          <v-icon size="small">
            mdi-chevron-right
          </v-icon>
        </template>
        <template v-slot:item="{ item, index }">
          <v-breadcrumbs-item
            :to="index < breadcrumbs.length - 1
              ? getDirectoryLink(item.path) : undefined"
            :disabled="index === breadcrumbs.length - 1"
          >
            <v-icon
              v-if="index === 0"
              size="small"
              class="mr-1"
            >
              mdi-folder-home-outline
            </v-icon>
            {{ item.title }}
          </v-breadcrumbs-item>
        </template>
      </v-breadcrumbs>

      <v-text-field
        :model-value="search"
        prepend-inner-icon="mdi-magnify"
        label="Search for files and directories..."
        density="compact"
        variant="outlined"
        class="coverage-search"
        hide-details
        clearable
        @update:model-value="emit('update:search', $event || '')"
      />
    </v-row>

    <v-data-table
      :headers="headers"
      :items="items"
      :loading="loading"
      :items-per-page-options="itemsPerPageOptions"
      items-per-page="50"
      item-value="path"
      loading-text="Loading test coverage..."
      :no-data-text="search
        ? 'No file or directory matches the search.'
        : 'This directory has no test coverage data.'"
      class="elevation-0"
    >
      <template #item.name="{ item }">
        <router-link
          :to="item.isFile
            ? getFileLink(item) : getDirectoryLink(item.path)"
          class="coverage-name"
          :title="item.path"
        >
          <v-icon size="small" class="mr-1">
            {{ item.isFile ? "mdi-file-code-outline" : "mdi-folder-outline" }}
          </v-icon>
          {{ item.name }}
        </router-link>
      </template>

      <template
        v-for="metric in metrics"
        :key="metric.id"
        #[`item.${percentKey(metric)}`]="{ item }"
      >
        <coverage-percentage
          :hit="item[metric.hit]"
          :found="item[metric.found]"
          :unit="metric.unit"
          :verb="metric.verb"
        />
        <div class="text-caption text-medium-emphasis">
          {{ item[metric.hit] }} / {{ item[metric.found] }}
        </div>
      </template>
    </v-data-table>
  </div>
</template>

<script setup>
import { computed } from "vue";

import CoveragePercentage from "./CoveragePercentage";
import { percentKey } from "./coverage-tree";

const props = defineProps({
  items: { type: Array, required: true },
  breadcrumbs: { type: Array, required: true },
  // The shown metrics (elements of METRICS of coverage-tree.js).
  metrics: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  search: { type: String, default: "" },
  // Functions which return the route location of a directory path and of a
  // file table item.
  getDirectoryLink: { type: Function, required: true },
  getFileLink: { type: Function, required: true }
});

const emit = defineEmits([ "update:search" ]);

// Percentages of entities without measured data are null. They are sorted
// as -1 so they are placed before the 0% entities.
const sortPercent = (a, b) => (a ?? -1) - (b ?? -1);

// One column per metric: the percentage bar with the "hit / found" counts.
const headers = computed(() => [
  {
    title: "Name",
    key: "name"
  },
  ...props.metrics.map(metric => ({
    title: `${metric.title} coverage`,
    key: percentKey(metric),
    sort: sortPercent
  }))
]);

const itemsPerPageOptions = [
  { value: 25, title: "25" },
  { value: 50, title: "50" },
  { value: 100, title: "100" },
  { value: -1, title: "All" }
];
</script>

<style lang="scss" scoped>
.coverage-search {
  max-width: 360px;
}

.coverage-breadcrumbs {
  font-family: monospace;
}

.coverage-name {
  font-family: monospace;
  text-decoration: none;
  white-space: nowrap;
}

// Narrower coverage bars, so a column of every metric fits next to each
// other on a laptop screen.
:deep(.coverage-percentage) {
  min-width: 112px;

  .coverage-bar {
    max-width: 56px;
  }
}
</style>
