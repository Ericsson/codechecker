<template>
  <div id="statistics">
    <checker-statistics />
    <severity-statistics />
  </div>
</template>

<script>
import CheckerStatistics from "@/components/CheckerStatistics";
import SeverityStatistics from "@/components/SeverityStatistics";

export default {
  name: "Statistics",
  components: {
    CheckerStatistics,
    SeverityStatistics
  }
}
</script>
