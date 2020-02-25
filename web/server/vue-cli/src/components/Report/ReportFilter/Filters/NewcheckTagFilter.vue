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
    updateReportFilter() {
      const selectedTagIds =
        [].concat(...this.selectedItems.map(item => item.tagIds));

      if (selectedTagIds.length) {
        this.setCmpData({ runTag: selectedTagIds });
      } else {
        this.setCmpData({ runTag: null });
      }
    },
  }
};
</script>
