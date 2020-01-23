<script>
import BaselineRunFilter from "./BaselineRunFilter";

export default {
  name: 'NewcheckRunFilter',
  mixins: [ BaselineRunFilter ],

  data() {
    return {
      id: "newcheck"
    };
  },

  methods: {
    updateReportFilter() {
      const selectedRunIds =
        [].concat(...this.selectedItems.map(item => item.runIds));

      if (selectedRunIds.length) {
        this.setCmpData({
          runIds: selectedRunIds
        });
      } else {
        this.setCmpData(null);
      }
    },
  }
}
</script>
