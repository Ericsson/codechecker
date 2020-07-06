<script>
import BaselineTagFilter from "./BaselineTagFilter";

export default {
  name: "NewcheckTagFilter",
  mixins: [ BaselineTagFilter ],

  data() {
    return {
      id: "run-tag-newcheck"
    };
  },

  methods: {
    async updateReportFilter() {
      const tagIds = await this.getSelectedTagIds();
      if (tagIds.length) {
        this.setCmpData({ runTag: tagIds });
      } else {
        this.setCmpData({ runTag: null });
      }
    },
  }
};
</script>
