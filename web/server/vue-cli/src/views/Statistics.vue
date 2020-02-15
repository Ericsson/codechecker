<template>
  <splitpanes class="default-theme">
    <pane size="20">
      TODO: Statistics filter
    </pane>
    <pane>
      <checker-statistics />
      <severity-statistics />
    </pane>
  </splitpanes>
</template>

<script>
import { Splitpanes, Pane } from "splitpanes";

import CheckerStatistics from "@/components/CheckerStatistics";
import SeverityStatistics from "@/components/SeverityStatistics";

export default {
  name: "Statistics",
  components: {
    Splitpanes,
    Pane,
    CheckerStatistics,
    SeverityStatistics
  }
}
</script>
