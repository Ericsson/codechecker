<template>
  <v-data-table
    :headers="headers"
    :items="value"
    :loading="loading"
    loading-text="Loading cleanup plans..."
    no-data-text="There aren't any cleanup plan that match."
    item-key="name"
  >
    <template v-slot:item.dueDate="{ item }">
      <span v-if="item.dueDate">
        <due-date
          :value="item.dueDate"
          :hide-label="true"
        />
      </span>
    </template>

    <template v-slot:item.closedAt="{ item }">
      <span v-if="item.closedAt">
        {{ item.closedAt | fromUnixTime }}
      </span>
    </template>

    <template v-slot:item.actions="{ item }">
      <v-btn
        class="edit-btn"
        color="primary"
        small
        @click="$emit('edit', item)"
      >
        <v-icon small class="mr-1">
          mdi-pencil
        </v-icon>
        Edit
      </v-btn>

      <v-btn
        v-if="item.closedAt"
        class="reopen-btn white--text"
        small
        color="green"
        @click="$emit('reopen', item)"
      >
        <v-icon small class="mr-1">
          mdi-refresh-circle
        </v-icon>
        Reopen
      </v-btn>

      <v-btn
        v-else
        class="close-btn white--text"
        small
        color="green"
        @click="$emit('close', item)"
      >
        <v-icon small class="mr-1">
          mdi-close-circle
        </v-icon>
        Close
      </v-btn>

      <v-btn
        class="remove-btn"
        small
        color="error"
        @click="$emit('remove', item)"
      >
        <v-icon small class="mr-1">
          mdi-trash-can-outline
        </v-icon>
        Delete
      </v-btn>
    </template>
  </v-data-table>
</template>

<script>
import DueDate from "./DueDate";

export default {
  name: "ListCleanupPlansTable",
  components: {
    DueDate
  },
  props: {
    value: { type: Array, required: true },
    loading: { type: Boolean, default: false },
    hideCols: { type: Array, default: () => [] }
  },
  computed: {
    headers() {
      return [
        {
          text: "Name",
          value: "name",
          sortable: true
        },
        {
          text: "Description",
          value: "description",
          sortable: true
        },
        {
          text: "Due date",
          value: "dueDate",
          sortable: true
        },
        {
          text: "Closed at",
          value: "closedAt",
          sortable: true
        },
        {
          text: "Actions",
          value: "actions",
          sortable: false
        },
      ].filter(c => !this.hideCols.includes(c.value));
    }
  }
};
</script>
