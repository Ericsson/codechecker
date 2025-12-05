<template>
  <v-data-table
    :headers="headers"
    :items="items"
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
        {{ fromUnixTime(item.closedAt) }}
      </span>
    </template>

    <template v-slot:item.actions="{ item }">
      <v-btn
        class="edit-btn mr-2"
        color="primary"
        size="small"
        variant="tonal"
        prepend-icon="mdi-pencil-outline"
        @click="emit('edit', item)"
      >
        Edit
      </v-btn>

      <v-btn
        v-if="item.closedAt"
        class="reopen-btn mr-2"
        size="small"
        color="green"
        variant="tonal"
        prepend-icon="mdi-refresh"
        @click="emit('reopen', item)"
      >
        Reopen
      </v-btn>

      <v-btn
        v-else
        class="close-btn mr-2"
        size="small"
        color="green"
        variant="tonal"
        prepend-icon="mdi-close-circle-outline"
        @click="emit('close', item)"
      >
        Close
      </v-btn>

      <v-btn
        class="remove-btn"
        size="small"
        color="error"
        variant="tonal"
        prepend-icon="mdi-trash-can-outline"
        @click="emit('remove', item)"
      >
        Delete
      </v-btn>
    </template>
  </v-data-table>
</template>

<script setup>
import { fromUnixTime } from "@/filters/from-unix-time";
import { computed } from "vue";
import DueDate from "./DueDate";

const props = defineProps({
  items: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  hideCols: { type: Array, default: () => [] }
});

const emit = defineEmits([ "remove", "close", "reopen", "edit" ]);

const headers = computed(() => [
  {
    title: "Name",
    key: "name",
    sortable: true
  },
  {
    title: "Description",
    key: "description",
    sortable: true
  },
  {
    title: "Due date",
    key: "dueDate",
    sortable: true
  },
  {
    title: "Closed at",
    key: "closedAt",
    sortable: true
  },
  {
    title: "Actions",
    key: "actions",
    sortable: false
  },
].filter(c => !props.hideCols.includes(c.value)));
</script>
