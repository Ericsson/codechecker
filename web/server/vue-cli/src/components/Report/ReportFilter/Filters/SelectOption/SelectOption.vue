<template>
  <filter-toolbar
    :title="title"
    @clear="clear"
  >
    <template v-slot:append-toolbar-items>
      <v-menu
        v-model="menu"
        :close-on-content-click="false"
        :nudge-width="400"
        offset-x
      >
        <v-progress-linear
          v-if="loading"
          indeterminate
          size="64"
        />

        <template v-slot:activator="{ on }">
          <v-btn
            icon
            small
            v-on="on"
          >
            <v-icon>mdi-settings</v-icon>
          </v-btn>
        </template>

        <items
          :items="items"
          :selected-items="prevSelectedItems"
          :search="search"
          :multiple="multiple"
          @select="select"
        >
          <template v-slot:icon="{ item }">
            <slot name="icon" :item="item" />
          </template>
          <template v-slot:no-items>
            <slot name="no-items" />
          </template>
        </items>
      </v-menu>
    </template>

    <items-selected
      :selected-items="selectedItems"
      @select="select"
    >
      <template v-slot:icon="{ item }">
        <slot name="icon" :item="item" />
      </template>
    </items-selected>
  </filter-toolbar>
</template>

<script>
import FilterToolbar from "../Layout/FilterToolbar";
import Items from "./Items";
import ItemsSelected from "./ItemsSelected";

export default {
  name: "SelectOption",
  components: {
    FilterToolbar,
    Items,
    ItemsSelected
  },
  props: {
    title: { type: String, required: true },
    items: { type: Array, required: true },
    fetchItems: { type: Function, required: true },
    selectedItems: { type: Array, default: () => [] },
    multiple: { type: Boolean, default: true },
    search: { type: Object, default: null },
    loading: { type: Boolean, default: false }
  },
  data() {
    return {
      menu: false,
      prevSelectedItems: null
    };
  },

  watch: {
    menu(show) {
      if (show) {
        this.prevSelectedItems =
          JSON.parse(JSON.stringify(this.selectedItems));
      } else {
        // TODO: check if the selected items are changed.
        const changed = true;

        if (!changed) return;

        this.selectedItems.splice(0, this.selectedItems.length,
          ...this.prevSelectedItems);
      }
    }
  },
  created() {
    const unwatch = this.$watch("menu", () => {
      if (!this.items.length) {
        this.fetchItems();
      }

      unwatch();
    });
  },

  methods: {
    select(selectedItems) {
      this.prevSelectedItems = selectedItems;
    },
    clear() {
      this.$emit("clear");
    }
  }
}
</script>
