<script>
import BaselineOpenReportsDateFilter from "./BaselineOpenReportsDateFilter";

export default {
  name: "ComparedToOpenReportsDateFilter",
  mixins: [ BaselineOpenReportsDateFilter ],

  data() {
    return {
      id: "compared-to-open-reports-date"
    };
  },

  methods: {
    async updateReportFilter() {
      this.setCmpData({
        openReportsDate: this.date ? this.getUnixTime(this.date) : null
      });
    }
  }
};
</script>
