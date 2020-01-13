<template>
  <v-list
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
        v-for="item in items"
        :key="item.id"
        :value="item"
        class="my-1"
      >
        <template v-slot:default="{ active }">
          <v-list-item-action class="mr-5">
            <v-checkbox :value="active" color="#28a745" />
          </v-list-item-action>

          <v-list-item-icon class="mr-2">
            <slot name="icon" :item="item" />
          </v-list-item-icon>

          <v-list-item-content>
            <v-list-item-title v-text="item.title" />
          </v-list-item-content>

          <v-chip color="#878d96" outlined>
            {{ item.count }}
          </v-chip>
        </template>
      </v-list-item>
    </v-list-item-group>
  </v-list>
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

export default {
  name: 'SelectOptionItems',
  components: {
    VList, VListItem, VListItemAction, VListItemContent, VListItemIcon,
    VListItemGroup, VListItemTitle, VCheckbox, VChip
  },
  props: {
    items: { type: Array, required: true },
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
