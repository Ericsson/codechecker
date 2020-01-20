import BaseFilterMixin from './BaseFilter.mixin';

export default {
  name: 'BaseSelectOptionFilter',
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
    encodeValue(severityId) {
      return severityId;
    },

    decodeValue(severityName) {
      return severityName;
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
            return {
              id: this.decodeValue(s),
              title: s,
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

    updateReportFilter() {},

    updateSelectedItems() {
      this.selectedItems.forEach((selectedItem) => {
        const item = this.items.find((i) => i.id === selectedItem.id);
        if (item) {
          selectedItem.count = item.count;
        }
      });
    },

    fetchItems() {}
  }
}