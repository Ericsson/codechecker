<script>
import { mapMutations } from 'vuex'
import { SET_CMP_DATA } from "@/store/mutations.type";

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
    ...mapMutations([
      SET_CMP_DATA
    ]),

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
