<script>
export default {
  name: "BaseStatistics",
  props: {
    bus: { type: Object, required: true }
  },

  data() {
    return {
      statistics: []
    };
  },

  activated() {
    this.bus.$on("refresh", this.fetchStatistics);
  },

  deactivated() {
    this.bus.$off("refresh", this.fetchStatistics);
  },

  mounted() {
    // The fetchStatistics function which initalizes this component is called
    // dynamically by the parent component. If Hot Module Replacement is
    // enabled and this component will be replaced then this initialization
    // will not be made. For this reason on component replacement we will save
    // the data and we will initalize the new component with this data.
    if (process.env.NODE_ENV !== "production") {
      if (module.hot) {
        if (module.hot.data) {
          this.statistics = module.hot.data.statistics;
        }

        module.hot.dispose(data => data["statistics"] = this.statistics);
      }
    }
  },

  methods: {
    fetchStatistics() {},
  }
};
</script>