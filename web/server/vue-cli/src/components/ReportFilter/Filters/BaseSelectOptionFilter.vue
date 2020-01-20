<script>
import BaseFilter from './BaseFilter';

export default {
  name: 'BaseSelectOptionFilter',
  extends: BaseFilter,

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

  created() {
    this.initByUrl();
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
      const state = [].concat(this.$route.query[this.id] || []);
      if (state.length) {
        this.selectedItems = state.map((s) => {
          return {
            id: this.decodeValue(s),
            title: s,
            count: "N/A"
          };
        });

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
</script>
