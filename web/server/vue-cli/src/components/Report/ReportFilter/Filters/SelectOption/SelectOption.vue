<template>
  <filter-toolbar
    :title="title"
    @clear="clear"
  >
    <template v-slot:prepend-toolbar-title>
      <slot name="prepend-toolbar-title" />
    </template>

    <template v-slot:prepend-toolbar-items>
      <slot name="prepend-toolbar-items" />
    </template>

    <template v-slot:append-toolbar-items>
      <v-menu
        v-model="menu"
        content-class="settings-menu"
        :close-on-content-click="false"
        :nudge-width="300"
        :max-width="600"
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
            class="settings-btn"
            v-on="on"
          >
            <v-icon>mdi-settings</v-icon>
          </v-btn>
        </template>

        <items
          :items.sync="items"
          :selected-items="prevSelectedItems"
          :search="search"
          :multiple="multiple"
          @apply="apply"
          @cancel="cancel"
          @select="select"
        >
          <template v-slot:icon="{ item }">
            <slot name="icon" :item="item" />
          </template>
          <template v-slot:no-items>
            <slot name="no-items" />
          </template>
          <template v-slot:title="{ item }">
            <slot name="title" :item="item" />
          </template>
        </items>
      </v-menu>
    </template>

    <items-selected
      :selected-items="selectedItems"
      @update:select="updateSelectedItems"
    >
      <template v-slot:icon="{ item }">
        <slot name="icon" :item="item" />
      </template>

      <template v-slot:title="{ item }">
        <slot name="title" :item="item" />
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
    bus: { type: Object, required: true },
    fetchItems: { type: Function, required: true },
    selectedItems: { type: Array, default: () => [] },
    multiple: { type: Boolean, default: true },
    search: { type: Object, default: null },
    loading: { type: Boolean, default: false }
  },
  data() {
    return {
      items: [],
      reloadItems: true,
      menu: false,
      prevSelectedItems: [],
      cancelled: false
    };
  },

  watch: {
    async menu(show) {
      if (show) {
        this.cancelled = false;

        if (this.reloadItems) {
          this.items = await this.fetchItems();
          this.reloadItems = false;
        }

        this.prevSelectedItems =
          JSON.parse(JSON.stringify(this.selectedItems));
      } else if (!this.cancelled) {
        this.apply();
      }
    }
  },

  mounted() {
    this.bus.$on("update", () => this.reloadItems = true);
  },

  methods: {
    apply() {
      if (!this.filterIsChanged()) return;
      this.updateSelectedItems(this.prevSelectedItems);
    },

    /**
     * Returns true if the filter is changed, else false.
     */
    filterIsChanged() {
      if (this.selectedItems.length !== this.prevSelectedItems.length) {
        return true;
      }

      const curr = this.selectedItems.map(item => item.title).sort();
      const prev = this.prevSelectedItems.map(item => item.title).sort();

      for (let i = 0; i < curr.length; ++i) {
        if (curr[i] !== prev[i]) return true;
      }

      return false;
    },

    cancel() {
      this.cancelled = true;
      this.menu = false;
    },

    select(selectedItems) {
      this.prevSelectedItems = selectedItems;
    },

    updateSelectedItems(selectedItems) {
      this.$emit("input", selectedItems);
    },

    clear() {
      this.$emit("clear");
    }
  }
};
</script>
