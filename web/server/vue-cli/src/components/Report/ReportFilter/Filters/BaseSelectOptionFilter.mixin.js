import Vue from "vue";
import BaseFilterMixin from "./BaseFilter.mixin";

export default {
  name: "BaseSelectOptionFilter",
  mixins: [ BaseFilterMixin ],

  data() {
    return {
      id: -1,
      selectedItems: [],
      bus: new Vue(),
      loading: false,
      defaultValues: null
    };
  },

  methods: {
    async setSelectedItems(selectedItems, updateUrl=true) {
      this.selectedItems = selectedItems;
      await this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    encodeValue(value) {
      return value;
    },

    decodeValue(value) {
      return value;
    },

    titleFormatter(id) {
      return this.encodeValue(id);
    },

    getUrlState() {
      const state =
        this.selectedItems.map(item => this.encodeValue(item.id));

      return { [this.id]: state.length ? state : undefined };
    },

    getIconClass() {},

    initByUrl() {
      return new Promise(resolve => {
        let state = [].concat(this.$route.query[this.id] || []);
        if (!state.length && this.defaultValues) {
          state = this.defaultValues;
        }

        if (!state.length) return resolve();

        const selectedItems = state.map(s => {
          const id = this.decodeValue(s);
          return {
            id: id,
            title: this.titleFormatter(id),
            count: "N/A",
            icon: this.getIconClass(id)
          };
        });
        this.setSelectedItems(selectedItems, false);

        resolve();
      });
    },

    async afterInit() {
      this.registerWatchers();
      this.update();
      this.initPanel();
    },

    initPanel() {
      this.panel = this.selectedItems.length > 0;
    },

    async update() {
      this.bus.$emit("update");

      if (!this.selectedItems.length) return;

      const items = await this.fetchItems({
        limit: this.selectedItems.length,
        query: this.selectedItems.map(item => item.id)
      });

      this.selectedItems.forEach(selectedItem => {
        const item = items.find(i => i.id === selectedItem.id);
        selectedItem.count = item ? item.count : null;
        selectedItem.value = item ? item.value : null;
      });
    },

    filterItems(value) {
      return this.fetchItems({ query: value ? [ `${value}*` ] : null });
    },

    clear(updateUrl) {
      this.setSelectedItems([], updateUrl);
    },

    async onRunIdsChange() {
      this.update();
    },

    async onReportFilterChange() {
      this.update();
    }
  }
};