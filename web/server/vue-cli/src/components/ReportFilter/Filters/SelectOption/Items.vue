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
        :multiple="multiple"
        active-class="light-blue--text"
        lighten-4
      >
        <v-list-item
          v-for="item in items"
          :key="item.id"
          :value="item.id"
          class="my-1"
        >
          <template v-slot:default="{ active }">
            <v-list-item-action class="ma-1 mr-5">
              <v-checkbox
                :input-value="active"
                color="#28a745"
              />
            </v-list-item-action>

            <v-list-item-icon class="ma-1 mr-2">
              <slot name="icon" :item="item" />
            </v-list-item-icon>

            <v-list-item-content>
              <v-list-item-title v-text="item.title" />
            </v-list-item-content>

            <v-chip
              v-if="item.count !== undefined"
              color="#878d96"
              outlined
              small
            >
              {{ item.count }}
            </v-chip>
          </template>
        </v-list-item>
      </v-list-item-group>

      <v-list-item v-else>
        <slot name="no-items">
          <v-list-item-icon>
            <v-icon>mdi-help-rhombus-outline</v-icon>
          </v-list-item-icon>
          No items
        </slot>
      </v-list-item>
    </v-list>
  </v-card>
</template>

<script>
export default {
  name: "SelectOptionItems",
  props: {
    items: { type: Array, required: true },
    selectedItems: { type: Array, required: true },
    multiple: { type: Boolean, default: true },
    search: { type: Object, default: null },
  },
  computed: {
    selected: {
      get() {
        const ids = this.selectedItems.map((item) => item.id);
        return this.multiple ? ids : ids[0]
      },
      set(value) {
        const values = this.multiple ? value : [ value ];
        const selectedItems = this.items.filter((item) => {
          return values.includes(item.id);
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
