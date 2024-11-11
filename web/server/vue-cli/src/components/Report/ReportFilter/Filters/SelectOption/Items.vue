<template>
  <v-card flat>
    <slot name="prepend-toolbar" />

    <v-toolbar
      v-if="search"
      class="pa-2"
      dense
      flat
    >
      <v-text-field
        ref="search"
        v-model="searchTxt"
        autofocus
        hide-details
        prepend-icon="mdi-magnify"
        single-line
        :label="search.placeHolder"
        @input="filter"
      />
    </v-toolbar>

    <slot name="append-toolbar" />

    <v-list
      class="pa-2 overflow-y-auto"
      dense
      :max-height="300"
    >
      <v-list-item-group
        v-if="searchTxt && search.regexLabel"
        v-model="selectedRgx"
        active-class="white--text"
        lighten-4
      >
        <v-list-item
          class="my-1 regex-label"
          :value="searchTxt"
          dark
        >
          <template v-slot:default="{ active }">
            <v-list-item-action class="ma-1 mr-5">
              <v-checkbox
                :input-value="active"
                color="#28a745"
              />
            </v-list-item-action>

            <v-list-item-content>
              <v-list-item-title>
                {{ search.regexLabel }}: {{ searchTxt }}
              </v-list-item-title>
            </v-list-item-content>
          </template>
        </v-list-item>
      </v-list-item-group>

      <v-list-item-group
        v-if="items.length"
        v-model="selected"
        :multiple="multiple"
        active-class="light-blue--text"
        lighten-4
      >
        <v-hover
          v-for="item in formattedItems"
          :key="item.id"
          v-slot:default="{ hover }"
        >
          <v-list-item
            :value="item.id"
            class="my-1"
            :disabled="!multiple && selected === item.id"
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
                <slot name="title" :item="item">
                  <v-list-item-title :title="item.title">
                    {{ item.title }}
                  </v-list-item-title>
                </slot>
              </v-list-item-content>

              <slot
                name="prepend-count"
                :item="item"
                :hover="hover"
              />

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
        </v-hover>
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

    <div
      v-if="limit"
      class="text-center text--secondary"
    >
      <span v-if="limit === items.length">Only the first</span>
      <i>{{ items.length }}</i> item(s) shown.
    </div>

    <v-card-actions>
      <v-spacer />

      <v-btn
        text
        class="cancel-btn"
        color="grey"
        @click="$emit('cancel')"
      >
        <v-icon left>
          mdi-close-circle-outline
        </v-icon>
        Cancel
      </v-btn>

      <v-btn
        text
        class="apply-btn"
        color="primary"
        @click="apply"
      >
        <v-icon left>
          mdi-check-circle-outline
        </v-icon>
        Apply
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import _ from "lodash";

export default {
  name: "SelectOptionItems",
  props: {
    items: { type: Array, required: true },
    format: { type: Function, default: null },
    limit: { type: Number, default: null },
    selectedItems: { type: Array, required: true },
    multiple: { type: Boolean, default: true },
    search: { type: Object, default: null },
  },

  data() {
    return {
      searchTxt: null,
    };
  },

  computed: {
    formattedItems() {
      if (!this.format) return this.items;

      return this.items.map(i => this.format(i));
    },

    selected: {
      get() {
        const ids = this.selectedItems.map(item => item.id);
        return this.multiple ? ids : ids[0];
      },
      set(id) {
        const selectedIds = this.multiple ? id : [ id ];

        const selectedItems = this.selectedItems
          // Filter elements which can be found in the previously selected item
          // list but not in the current item list.
          .filter(s => this.items.findIndex(item => item.id === s.id) === -1)
          // Add new elements which can be found in the current item list and
          // in the currently selected ids list.
          .concat(this.items.filter(item => selectedIds.includes(item.id)));

        this.$emit("select", selectedItems);
      }
    },

    selectedRgx: {
      get() {
        return this.selectedItems.find(item => item.id === this.searchTxt)
          ? this.searchTxt
          : null;
      },
      set(value) {
        const selectedItems = [ ...this.selectedItems ];
        const idx =
          selectedItems.findIndex(item => item.id === this.searchTxt);

        if (!value && idx !== -1) {
          selectedItems.splice(idx, 1);
        } else if (value && idx === -1) {
          selectedItems.push({ id: value, title: value });
        }

        this.$emit("select", selectedItems);
      }
    }
  },

  methods: {
    filter: _.debounce(async function (value) {
      const items = await this.search.filterItems(value);
      this.$emit("update:items", items);
    }, 500),

    apply() {
      this.$emit("apply", this.selectedItems);
      this.$emit("apply:finished");
    }
  }
};
</script>

<style lang="scss">
.regex-label {
  background-color: var(--v-primary-base);
  color: white;
}
</style>