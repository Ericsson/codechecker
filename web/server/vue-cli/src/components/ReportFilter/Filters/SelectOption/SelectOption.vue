<template>
  <v-card flat>
    <v-toolbar flat>
      <v-toolbar-title>{{ title }}</v-toolbar-title>
      <v-spacer />
      <v-toolbar-items>
        <v-btn icon @click="clear">
          <v-icon>mdi-delete</v-icon>
        </v-btn>
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
            <v-btn icon v-on="on">
              <v-icon>mdi-settings</v-icon>
            </v-btn>
          </template>

          <items
            :items="items"
            :selected-items="selectedItems"
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
      </v-toolbar-items>
    </v-toolbar>

    <items-selected
      :selected-items="selectedItems"
      @select="select"
    >
      <template v-slot:icon="{ item }">
        <slot name="icon" :item="item" />
      </template>
    </items-selected>
  </v-card>
</template>

<script>
import Items from "./Items";
import ItemsSelected from "./ItemsSelected";

export default {
  name: "SelectOption",
  components: {
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
      menu: false
    };
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
      this.selectedItems.splice(0, this.selectedItems.length, ...selectedItems);
    },
    clear() {
      this.selectedItems.splice(0, this.selectedItems.length);
    }
  }
}
</script>
