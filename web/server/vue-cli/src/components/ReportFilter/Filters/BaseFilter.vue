<script>
export default {
  name: 'BaseFilter',

  methods: {
    getUrlState() {
      return {};
    },

    initByUrl() {},

    updateUrl() {
      const state = this.getUrlState();
      const queryParams = Object.assign({}, this.$route.query, state);
      this.$router.replace({ query: queryParams }).catch(() => {});
    },

    updateReportFilter() {},

    updateSelectedItems() {},

    fetchItems() {}
  }
}
</script>
