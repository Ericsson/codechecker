<template>
  <v-card flat>
    <v-toolbar
      v-if="search"
      class="pa-2"
      dense
      flat
    >
      <v-text-field
        hide-details
        prepend-icon="mdi-magnify"
        single-line
        :label="search.placeHolder"
        @input="filter"
      />
    </v-toolbar>

    <v-list
      class="pa-2"
      dense
    >
      <v-list-item-group
        v-if="items.length"
        v-model="selected"
        active-class="light-blue--text"
        lighten-4
        multiple
      >
        <v-list-item
          v-for="item in items"
          :key="item.id"
          :value="item.id"
          class="my-1"
        >
          <template v-slot:default="{ active }">
            <v-list-item-action class="mr-5">
              <v-checkbox
                :input-value="active"
                color="#28a745"
              />
            </v-list-item-action>

            <v-list-item-icon class="mr-2">
              <slot name="icon" :item="item" />
            </v-list-item-icon>

            <v-list-item-content>
              <v-list-item-title v-text="item.title" />
            </v-list-item-content>

            <v-chip
              v-if="item.count !== undefined"
              color="#878d96"
              outlined
            >
              {{ item.count }}
            </v-chip>
          </template>
        </v-list-item>
      </v-list-item-group>

      <v-list-item v-else>
        <v-list-item-icon>
          <v-icon>mdi-help-rhombus-outline</v-icon>
        </v-list-item-icon>
        No items
      </v-list-item>
    </v-list>
  </v-card>
</template>

<script>
import {
  VList,
  VListItem,
  VListItemAction,
  VListItemContent,
  VListItemIcon,
  VListItemGroup,
  VListItemTitle
} from "Vuetify/VList";
import VCheckbox from "Vuetify/VCheckbox/VCheckbox";
import VChip from "Vuetify/VChip/VChip";
import VIcon from "Vuetify/VIcon/VIcon";
import { VCard } from "Vuetify/VCard";
import VToolbar from "Vuetify/VToolbar/VToolbar";
import VTextField from "Vuetify/VTextField/VTextField";

export default {
  name: "SelectOptionItems",
  components: {
    VList, VListItem, VListItemAction, VListItemContent, VListItemIcon,
    VListItemGroup, VListItemTitle, VCheckbox, VChip, VIcon, VCard, VToolbar,
    VTextField
  },
  props: {
    items: { type: Array, required: true },
    selectedItems: { type: Array, required: true },
    search: { type: Object, default: null },
  },
  computed: {
    selected: {
      get() {
        return this.selectedItems.map((item) => item.id);
      },
      set(value) {
        const selectedItems = this.items.filter((item) => {
          return value.includes(item.id);
        });

        this.$emit("select", selectedItems)
      }
    }
  },
  methods: {
    filter(value) {
      this.search.filterItems(value);
    }
  }
}
</script>
