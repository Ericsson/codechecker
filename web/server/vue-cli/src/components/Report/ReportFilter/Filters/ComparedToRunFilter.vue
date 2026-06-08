<script>
import BaselineRunFilter from "./BaselineRunFilter";

export default {
  name: "ComparedToRunFilter",
  mixins: [ BaselineRunFilter ],

  data() {
    return {
      id: "newcheck",
      runTagId: "run-tag-newcheck",
    };
  },

  methods: {
    async updateReportFilter() {
      const selectedRunIds = await this.getSelectedRunIds();
      const selectedTagIds = this.selectedTagItems.map(t => t.id);

      if (selectedRunIds.length || selectedTagIds.length) {
        this.setCmpData({
          runIds: selectedRunIds.length ? selectedRunIds : null,
          runTag: selectedTagIds.length ? selectedTagIds : null
        });
      } else {
        this.setCmpData(null);
      }
    }
  }
};
</script>
