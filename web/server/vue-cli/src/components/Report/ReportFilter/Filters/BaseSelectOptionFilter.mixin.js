import BaseFilterMixin from "./BaseFilter.mixin";

export default {
  name: "BaseSelectOptionFilter",
  mixins: [ BaseFilterMixin ],

  data() {
    return {
      id: -1,
      selectedItems: [],
      items: [],
      loading: false
    };
  },

  watch: {
    items() {
      this.updateSelectedItems();
    }
  },

  methods: {
    update() {
      if (!this.selectedItems.length) return;

      this.fetchItems({
        limit: this.selectedItems.length,
        query: this.selectedItems.map(item => item.id)
      });
    },

    setSelectedItems(selectedItems, updateUrl=true) {
      this.selectedItems = selectedItems;
      this.updateReportFilter();

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

    initByUrl() {
      return new Promise(resolve => {
        const state = [].concat(this.$route.query[this.id] || []);
        if (state.length) {
          const selectedItems = state.map(s => {
            const id = this.decodeValue(s);
            return {
              id: id,
              title: this.titleFormatter(id),
              count: "N/A"
            };
          });
          this.setSelectedItems(selectedItems, false);
        }

        resolve();
      });
    },

    afterInit() {
      this.registerWatchers();

      if (this.selectedItems.length) {
        this.fetchItems({
          limit: this.selectedItems.length,
          query: this.selectedItems.map(item => item.id)
        });
      }
    },

    updateSelectedItems() {
      this.selectedItems.forEach(selectedItem => {
        const item = this.items.find(i => i.id === selectedItem.id);
        selectedItem.count = item ? item.count : null;
      });
    },

    filterItems(value) {
      this.fetchItems({
        query: value ? `${value}*` : null
      });
    },

    clear(updateUrl) {
      this.setSelectedItems([], updateUrl);
    }
  }
};