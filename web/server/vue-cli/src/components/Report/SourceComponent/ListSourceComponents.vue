<template>
  <edit-source-component-dialog
    v-model="editDialog"
    :source-component="selectedComponent"
    @save:component="fetchSourceComponents"
  />
  <v-toolbar
    elevation="0"
    class="mb-4"
    color="transparent"
  >
    <div class="d-flex justify-end align-center ga-2 w-100">
      <v-btn
        color="primary"
        class="new-component-btn"
        variant="flat"
        height="40"
        @click="newSourceComponent"
      >
        New
      </v-btn>

      <v-btn
        icon="mdi-refresh"
        title="Reload components"
        color="primary"
        @click="fetchSourceComponents"
      />
    </div>
  </v-toolbar>

  <v-data-table
    :headers="headers"
    :items="processedComponents"
    :items-per-page="25"
    :items-per-page-options="itemsPerPageOptions"
    :loading="loading"
  >
    <template #item.key="{ item }">
      <ul class="component-value">
        <li
          v-for="value in item.$values"
          :key="value"
        >
          <span
            v-if="value.startsWith('+')"
            class="green-text"
          >
            {{ value }}
          </span>
          <span
            v-else
            class="error-text"
          >
            {{ value }}
          </span>
        </li>
      </ul>
    </template>

    <template v-slot:item.actions="{ item }">
      <v-btn
        class="edit-btn ml-2"
        icon="mdi-pencil"
        color="primary"
        size="small"
        variant="text"
        @click="editSourceComponent(item)"
      />
      <remove-source-component-dialog
        :source-component="item"
        @on:confirm="fetchSourceComponents"
      />
    </template>
  </v-data-table>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, onMounted, ref } from "vue";

import EditSourceComponentDialog from "./EditSourceComponentDialog";
import RemoveSourceComponentDialog from "./RemoveSourceComponentDialog";

const components = ref([]);
const loading = ref(false);
const selectedComponent = ref(null);
const editDialog = ref(false);

const itemsPerPageOptions = [
  { value: 25, title: "25" },
  { value: 50, title: "50" },
  { value: 100, title: "100" }
];

const headers = [
  {
    title: "Name",
    key: "name",
    sortable: true
  },
  {
    title: "Value",
    key: "value",
    sortable: true
  },
  {
    title: "Description",
    key: "description",
    sortable: true
  },
  {
    title: "Actions",
    key: "actions",
    sortable: false
  },
];

const processedComponents = computed(function() {
  return components.value.map(component => {
    return {
      ...component,
      $values: component.value.split(/\r|\n/)
    };
  });
});

onMounted(function() {
  fetchSourceComponents();
});

function fetchSourceComponents() {
  loading.value = true;
  ccService.getClient().getSourceComponents(null,
    handleThriftError(_components => {
      components.value = _components.filter(c =>
        !c.name.includes("auto-generated"));
      loading.value = false;
    }));
}

function editSourceComponent(component) {
  selectedComponent.value = component;
  editDialog.value = true;
}

function newSourceComponent() {
  selectedComponent.value = null;
  editDialog.value = true;
}
</script>

<style lang="scss" scoped>
.component-value {
  list-style-type: none;
  padding: 0;
}
</style>
