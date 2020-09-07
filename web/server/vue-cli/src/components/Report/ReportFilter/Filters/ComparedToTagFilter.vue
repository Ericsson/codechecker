<script>
import BaselineTagFilter from "./BaselineTagFilter";

export default {
  name: "ComparedToTagFilter",
  mixins: [ BaselineTagFilter ],

  data() {
    return {
      id: "run-tag-newcheck"
    };
  },

  methods: {
    async updateReportFilter() {
      const tagIds = await this.getSelectedTagIds();
      this.setCmpData({
        runTag: tagIds.length ? tagIds : null
      });
    },
  }
};
</script>
