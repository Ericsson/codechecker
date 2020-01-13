<template>
  <v-card>
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
            @select="select"
          >
            <template v-slot:icon="{ item }">
              <slot name="icon" :item="item" />
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
import { VCard } from "Vuetify/VCard";
import { VToolbar, VToolbarTitle, VToolbarItems } from "Vuetify/VToolbar";
import VSpacer from "Vuetify/VGrid/VSpacer";
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";
import VMenu from "Vuetify/VMenu/VMenu";
import VProgressLinear from "Vuetify/VProgressLinear/VProgressLinear";

import Items from './Items';
import ItemsSelected from './ItemsSelected';

export default {
  name: 'SelectOption',
  components: {
    VCard, VToolbar, VToolbarTitle, VToolbarItems, VSpacer, VBtn, VIcon, VMenu,
    VProgressLinear,
    Items, ItemsSelected
  },
  props: {
    title: { type: String, required: true },
    items: { type: Array, required: true },
    fetchItems: { type: Function, required: true },
    loading: { type: Boolean, default: false }
  },
  data() {
    return {
      menu: false,
      selectedItems: []
    };
  },

  created() {
    const unwatch = this.$watch("menu", () => {
      this.fetchItems();
      unwatch();
    });
  },

  methods: {
    select(selectedItems) {
      this.selectedItems = selectedItems;
    },
    clear() {
      this.selectedItems = [];
    }
  }
}
</script>
