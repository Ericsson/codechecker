<template>
  <v-list
    v-if="selected.length"
    class="pa-0"
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
        class="selected-item pa-0 px-1 ma-0 mb-1"
        :disabled="!multiple"
        dense
      >
        <v-list-item-icon class="ma-1 mr-2">
          <slot name="icon" :item="item" />
        </v-list-item-icon>

        <v-list-item-content class="pa-0">
          <slot name="title" :item="item">
            <v-list-item-title :title="item.title">
              {{ item.title }}
            </v-list-item-title>
          </slot>
        </v-list-item-content>

        <v-chip
          class="report-count"
          color="#878d96"
          outlined
          small
        >
          {{ item.count || item.count === 0 ? item.count : "N/A" }}
        </v-chip>

        <v-icon
          class="remove-btn font-weight-bold"
          color="error"
        >
          mdi-close
        </v-icon>
      </v-list-item>
    </v-list-item-group>
  </v-list>

  <v-list-item
    v-else
    dense
  >
    <v-list-item-content>
      <v-list-item-title>No filter</v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script>
export default {
  name: "ItemsSelected",
  props: {
    selectedItems: { type: Array, required: true },
    multiple: { type: Boolean, default: true }
  },
  computed: {
    selected: {
      get() {
        return this.selectedItems;
      },
      set(value) {
        this.$emit("update:select", value);
      }
    }
  }
};
</script>

<style lang="scss" scoped>
.v-list-item.v-list-item--dense {
  min-height: auto;
}

.selected-item {
  border: 1px solid var(--v-grey-lighten2);

  &:before {
    content: "";
    display: block;
    background-color: var(--v-primary-base);
    border-radius: 4px;
  }

  &:hover:before {
    background-color: var(--v-error-base);
  }

  .remove-btn {
    display:none;
  }

  &:hover {
    .report-count {
      display: none;
    }

    .remove-btn {
      display: block;
    }
  }
}
</style>
