<script>
import DetectionDateFilter from "./DetectionDateFilter";

export default {
  name: "FixDateFilter",
  mixins: [ DetectionDateFilter ],
  data() {
    return {
      title: "Fix date",
      fromDateTimeId: "fixed-after",
      toDateTimeId: "fixed-before",
      fromDateTimeLabel: "Fixed after...",
      toDateTimeLabel: "Fixed before...",
      filterFieldName: "fixed"
    };
  }
};
</script>
