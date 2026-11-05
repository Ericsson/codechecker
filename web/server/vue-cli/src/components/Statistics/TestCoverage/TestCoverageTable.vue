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

      <template #item.linePercent="{ item }">
        <coverage-percentage
          :hit="item.linesHit"
          :found="item.linesFound"
          unit="lines"
        />
      </template>

      <template #item.lines="{ item }">
        {{ item.linesHit }} / {{ item.linesFound }}
      </template>

      <template #item.functionPercent="{ item }">
        <coverage-percentage
          :hit="item.functionsHit"
          :found="item.functionsFound"
          unit="functions"
        />
      </template>

      <template #item.functions="{ item }">
        {{ item.functionsHit }} / {{ item.functionsFound }}
      </template>
    </v-data-table>
  </div>
</template>

<script setup>
import CoveragePercentage from "./CoveragePercentage";

defineProps({
  items: { type: Array, required: true },
  breadcrumbs: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  search: { type: String, default: "" },
  // Functions which return the route location of a directory path and of a
  // file table item.
  getDirectoryLink: { type: Function, required: true },
  getFileLink: { type: Function, required: true }
});

const emit = defineEmits([ "update:search" ]);

// Percentages of entities without executable lines or functions are null.
// They are sorted as -1 so they are placed before the 0% entities.
const sortPercent = (a, b) => (a ?? -1) - (b ?? -1);

const headers = [
  {
    title: "Name",
    key: "name"
  },
  {
    title: "Line coverage",
    key: "linePercent",
    sort: sortPercent
  },
  {
    title: "Executed / executable lines",
    key: "lines",
    align: "end",
    value: item => item.linesFound,
  },
  {
    title: "Function coverage",
    key: "functionPercent",
    sort: sortPercent
  },
  {
    title: "Executed functions / functions",
    key: "functions",
    align: "end",
    value: item => item.functionsFound
  }
];

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
</style>
