<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <report-filter
        v-fill-height
        :after-url-init="afterUrlInit"
      />
    </pane>
    <pane>
      <div v-fill-height>
        <checker-statistics />
        <severity-statistics />
      </div>
    </pane>
  </splitpanes>
</template>

<script>
import { Splitpanes, Pane } from "splitpanes";

import CheckerStatistics from "@/components/CheckerStatistics";
import { FillHeight } from "@/directives";
import SeverityStatistics from "@/components/SeverityStatistics";
import { ReportFilter } from "@/components/Report/ReportFilter";

export default {
  name: "Statistics",
  components: {
    Splitpanes,
    Pane,
    CheckerStatistics,
    ReportFilter,
    SeverityStatistics
  },
  directives: { FillHeight },
  methods: {
    afterUrlInit() {
      // TODO: implement this.
    }
  }
}
</script>
