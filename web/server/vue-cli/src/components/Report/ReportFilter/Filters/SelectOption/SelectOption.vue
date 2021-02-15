<template>
  <filter-toolbar
    :title="title"
    :panel="panel"
    @clear="clear"
  >
    <template v-slot:append-toolbar-title>
      <slot name="append-toolbar-title">
        <selected-toolbar-title-items
          v-if="selectedItems"
          :value="selectedItems"
        />
      </slot>
    </template>

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
            <v-icon>mdi-cog</v-icon>
          </v-btn>
        </template>

        <slot
          name="menu-content"
          :items="items"
          :prevSelectedItems="prevSelectedItems"
          :apply="applyFilters"
          :onApplyFinished="onApplyFinished"
          :cancel="cancel"
          :select="select"
        >
          <items
            :items.sync="items"
            :selected-items="prevSelectedItems"
            :search="search"
            :multiple="multiple"
            :limit="limit"
            @apply="applyFilters"
            @apply:finished="onApplyFinished"
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
        </slot>
      </v-menu>
    </template>

    <slot :updateSelectedItems="updateSelectedItems">
      <items-selected
        :selected-items="selectedItems"
        :multiple="multiple"
        @update:select="updateSelectedItems"
      >
        <template v-slot:icon="{ item }">
          <slot name="icon" :item="item" />
        </template>

        <template v-slot:title="{ item }">
          <slot name="title" :item="item" />
        </template>
      </items-selected>
    </slot>
  </filter-toolbar>
</template>

<script>
import FilterToolbar from "../Layout/FilterToolbar";
import {
  Items,
  ItemsSelected,
  SelectedToolbarTitleItems,
  filterIsChanged,
} from ".";

export default {
  name: "SelectOption",
  components: {
    FilterToolbar,
    Items,
    ItemsSelected,
    SelectedToolbarTitleItems
  },
  props: {
    title: { type: String, required: true },
    bus: { type: Object, required: true },
    fetchItems: { type: Function, required: true },
    selectedItems: { type: Array, default: () => [] },
    multiple: { type: Boolean, default: true },
    search: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    panel: { type: Boolean, default: false },
    limit: { type: Number, default: null },
    apply: {
      type: Function,
      default: function (selectedItems) {
        if (!filterIsChanged(this.selectedItems, selectedItems))
          return;

        this.updateSelectedItems(selectedItems);
      }
    }
  },
  data() {
    return {
      items: [],
      reloadItems: true,
      menu: false,
      prevSelectedItems: [],
      preventApply: false
    };
  },

  computed: {
    // Vue doesn't automatically bind functions passed to props property with
    // any Vue instance. For this reason we need to use this computed property
    // instead of apply function where we bind this to its parent Vue instance.
    applyFilters() {
      return this.apply.bind(this);
    }
  },

  watch: {
    async menu(show) {
      if (show) {
        this.$emit("on-menu-show");

        this.preventApply = false;

        if (this.reloadItems) {
          this.items = await this.fetchItems();
          this.reloadItems = false;
        }

        this.select(JSON.parse(JSON.stringify(this.selectedItems)));
      } else if (!this.preventApply) {
        this.applyFilters(this.prevSelectedItems);
      }
    }
  },

  mounted() {
    this.bus.$on("update", () => this.reloadItems = true);

    this.bus.$on("select", predicate => {
      const item = this.items.find(predicate);
      if (item &&
          this.prevSelectedItems.findIndex(i => i.id === item.id) === -1
      ) {
        // The item is not selected yet.
        this.prevSelectedItems.push(item);
      }
    });
  },

  methods: {
    onApplyFinished() {
      this.preventApply = true;
      this.menu = false;
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
      this.preventApply = true;
      this.menu = false;
      this.$emit("cancel");
    },

    select(selectedItems) {
      this.prevSelectedItems = selectedItems;
      this.$emit("select", this.prevSelectedItems);
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
