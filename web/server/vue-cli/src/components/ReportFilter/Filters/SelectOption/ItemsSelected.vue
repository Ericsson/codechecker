<template>
  <v-list
    v-if="selected.length"
    class="pa-2"
    dense
  >
    <v-list-item-group
      v-model="selected"
      active-class="light-blue--text"
      lighten-4
      multiple
    >
      <v-list-item
        v-for="item in selected"
        :key="item.id"
        :value="item"
        class="my-1"
      >
        <v-list-item-icon class="mr-2">
          <slot name="icon" :item="item" />
        </v-list-item-icon>

        <v-list-item-content>
          <v-list-item-title v-text="item.title" />
        </v-list-item-content>

        <v-chip color="#878d96" outlined>
          {{ item.count === undefined ? "N/A" : item.count }}
        </v-chip>
      </v-list-item>
    </v-list-item-group>
  </v-list>

  <v-list-item v-else>
    <v-list-item-content>
      <v-list-item-title>No filter</v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script>
import {
  VList,
  VListItem,
  VListItemContent,
  VListItemIcon,
  VListItemGroup,
  VListItemTitle
} from "Vuetify/VList";
import VChip from "Vuetify/VChip/VChip";

export default {
  name: 'ItemsSelected',
  components: {
    VList, VListItem, VListItemContent, VListItemIcon, VListItemGroup,
    VListItemTitle, VChip
  },
  props: {
    selectedItems: { type: Array, required: true }
  },
  computed: {
    selected: {
      get() {
        return this.selectedItems;
      },
      set(value) {
        this.$emit('select', value)
      }
    }
  }
}
</script>
