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
    selectedItems() {
      this.updateUrl();
      this.updateReportFilter();
    }
  },

  methods: {
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
      return {
        [this.id]: this.selectedItems.map((item) => this.encodeValue(item.id))
      };
    },

    initByUrl() {
      return new Promise((resolve) => {
        const state = [].concat(this.$route.query[this.id] || []);
        if (state.length) {
          this.selectedItems = state.map((s) => {
            const id = this.decodeValue(s);
            return {
              id: id,
              title: this.titleFormatter(id),
              count: "N/A"
            };
          });
        }

        resolve();
      });
    },

    afterUrlInit() {
      this.registerWatchers();

      if (this.selectedItems.length) {
        this.fetchItems();
      }
    },

    updateSelectedItems() {
      this.selectedItems.forEach((selectedItem) => {
        const item = this.items.find((i) => i.id === selectedItem.id);
        if (item) {
          selectedItem.count = item.count;
        }
      });
    },

    fetchItems() {},

    clear() {
      this.selectedItems = [];
    }
  }
}