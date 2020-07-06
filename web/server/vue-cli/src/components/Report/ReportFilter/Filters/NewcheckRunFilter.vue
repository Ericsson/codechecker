<script>
import BaselineRunFilter from "./BaselineRunFilter";

export default {
  name: "NewcheckRunFilter",
  mixins: [ BaselineRunFilter ],

  data() {
    return {
      id: "newcheck"
    };
  },

  methods: {
    async updateReportFilter() {
      const selectedRunIds = await this.getSelectedRunIds();

      if (selectedRunIds.length) {
        this.setCmpData({
          runIds: selectedRunIds
        });
      } else {
        this.setCmpData(null);
      }
    }
  }
};
</script>
