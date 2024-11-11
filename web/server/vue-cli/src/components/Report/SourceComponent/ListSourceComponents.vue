<template>
  <v-data-table
    :headers="headers"
    :items="processedComponents"
    :loading="loading"
  >
    <template v-slot:top>
      <edit-source-component-dialog
        :value.sync="editDialog"
        :source-component="selected"
        @save:component="fetchSourceComponents"
      />

      <remove-source-component-dialog
        :value.sync="removeDialog"
        :source-component="selected"
        @on:confirm="fetchSourceComponents"
      />

      <v-toolbar flat class="mb-4">
        <v-row>
          <v-col>
            <v-btn
              color="primary"
              class="new-component-btn mr-2"
              outlined
              @click="newSourceComponent"
            >
              New
            </v-btn>

            <v-btn
              icon
              title="Reload components"
              color="primary"
              @click="fetchSourceComponents"
            >
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
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
            class="green--text"
          >
            {{ value }}
          </span>
          <span
            v-else
            class="error--text"
          >
            {{ value }}
          </span>
        </li>
      </ul>
    </template>

    <template v-slot:item.actions="{ item }">
      <v-btn
        class="remove-btn"
        icon
        color="error"
        @click="removeSourceComponent(item)"
      >
        <v-icon>mdi-trash-can-outline</v-icon>
      </v-btn>

      <v-btn
        class="edit-btn"
        icon
        color="primary"
        @click="editSourceComponent(item)"
      >
        <v-icon>mdi-pencil</v-icon>
      </v-btn>
    </template>
  </v-data-table>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import EditSourceComponentDialog from "./EditSourceComponentDialog";
import RemoveSourceComponentDialog from "./RemoveSourceComponentDialog";

export default {
  name: "ListSourceComponents",
  components: {
    EditSourceComponentDialog,
    RemoveSourceComponentDialog
  },
  data() {
    return {
      components: [],
      loading: false,
      selected: null,
      editDialog: false,
      removeDialog: false,
      headers: [
        {
          text: "Name",
          value: "name",
          sortable: true
        },
        {
          text: "Value",
          value: "value",
          sortable: true
        },
        {
          text: "Description",
          value: "description",
          sortable: true
        },
        {
          text: "Actions",
          value: "actions",
          sortable: false
        },
      ]
    };
  },

  computed: {
    processedComponents() {
      return this.components.map(component => {
        return {
          ...component,
          $values: component.value.split(/\r|\n/)
        };
      });
    },
  },

  created() {
    this.fetchSourceComponents();
  },

  methods: {
    fetchSourceComponents() {
      this.loading = true;
      ccService.getClient().getSourceComponents(null,
        handleThriftError(components => {
          this.components = components.filter(c =>
            !c.name.includes("auto-generated"));
          this.loading = false;
        }));
    },

    editSourceComponent(component) {
      this.selected = component;
      this.editDialog = true;
    },

    newSourceComponent() {
      this.selected = null;
      this.editDialog = true;
    },

    removeSourceComponent(component) {
      this.selected = component;
      this.removeDialog = true;
    }
  }
};
</script>

<style lang="scss" scoped>
.component-value {
  list-style-type: none;
  padding: 0;
}
</style>
