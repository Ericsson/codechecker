<script>
import BaselineRunFilter from "./BaselineRunFilter";

export default {
  name: "ComparedToRunFilter",
  mixins: [ BaselineRunFilter ],

  data() {
    return {
      id: "newcheck"
    };
  },

  methods: {
    async updateReportFilter() {
      const selectedRunIds = await this.getSelectedRunIds();
      this.setCmpData({
        runIds: selectedRunIds.length ? selectedRunIds : null
      });
    }
  }
};
</script>
