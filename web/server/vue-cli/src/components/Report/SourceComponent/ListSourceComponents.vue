<template>
  <v-data-table
    :headers="headers"
    :items="processedComponents"
    :loading="loading"
  >
    <template v-slot:top>
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
        <v-row>
          <v-col class="d-flex justify-end align-center">
            <v-btn
              color="primary"
              class="new-component-btn mr-2"
              variant="outlined"
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
          </v-col>
        </v-row>
      </v-toolbar>
    </template>

    <template #item.value="{ item }">
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
      <remove-source-component-dialog
        :source-component="item"
        @on:confirm="fetchSourceComponents"
      />

      <v-btn
        class="edit-btn ml-2"
        icon="mdi-pencil"
        color="primary"
        variant="tonal"
        size="small"
        @click="editSourceComponent(item)"
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

const headers = [
  {
    title: "Name",
    value: "name",
    sortable: true
  },
  {
    title: "Value",
    value: "value",
    sortable: true
  },
  {
    title: "Description",
    value: "description",
    sortable: true
  },
  {
    title: "Actions",
    value: "actions",
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
