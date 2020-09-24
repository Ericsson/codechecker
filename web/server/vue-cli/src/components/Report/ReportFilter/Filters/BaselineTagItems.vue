<template>
  <items
    :items.sync="tags"
    :selected-items="selectedItems"
    :search="search"
    :limit="defaultLimit"
    @apply="apply"
    @cancel="cancel"
    @select="select"
  >
    <template v-slot:icon="{ item }">
      <slot name="icon" :item="item" />
    </template>
  </items>
</template>

<script>
import BaseFilterMixin from "./BaseFilter.mixin";
import Items from "./SelectOption/Items";

export default {
  name: "BaselineTagItems",
  components: { Items },
  mixins: [ BaseFilterMixin ],
  props: {
    selectedItems: { type: Array, default: null },
    selectedRunItems: { type: Array, default: null },
    bus: { type: Object, required: true },
    loadEventBus: { type: Object, required: true },
    fetchTags: { type: Function, required: true }
  },
  data() {
    return {
      loading: false,
      search: {
        placeHolder : "Search for run tags...",
        filterItems: this.filterItems
      },
      tags: [],
      reloadItems: false,
      filterOpt: {}
    };
  },
  computed: {
    selectedRunIds() {
      return this.selectedRunItems.map(i => i.runIds).flat();
    }
  },

  async mounted() {
    this.bus.$on("update", () => this.reloadItems = true);

    // Initalize tags.
    this.tags = await this.fetchTags();

    // Register on load events to update the items.
    this.loadEventBus.$on("load", async () => {
      if (!this.reloadItems) return;

      this.reload();
      this.reloadItems = false;
    });

    this.loadEventBus.$on("reload", async () => {
      this.reload();
      this.reloadItems = false;
    });
  },

  methods: {
    filterItems(value) {
      return this.fetchTags({ query: value ? [ `${value}*` ] : null });
    },

    async reload() {
      this.tags = await this.fetchTags(this.filterOpt);
    },

    apply() {
      this.$emit("apply", this.selectedRunItems);
    },

    select(selectedItems) {
      this.$emit("select", selectedItems);
    },

    cancel() {
      this.$emit("cancel");
      this.backToRuns();
    },

    backToRuns() {
      this.$emit("back-to-runs");
    }
  }
};
</script>
