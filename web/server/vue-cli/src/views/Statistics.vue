<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <report-filter
        v-fill-height
        :after-url-init="afterUrlInit"
        :namespace="namespace"
        :show-newcheck="false"
        :show-review-status="false"
        :show-remove-filtered-reports="false"
      />
    </pane>
    <pane>
      <div v-fill-height>
        <checker-statistics
          :namespace="namespace"
        />

        <severity-statistics
          :namespace="namespace"
        />
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

const namespace = "statistics";

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
  data() {
    return {
      namespace: namespace
    };
  },
  methods: {
    afterUrlInit() {
      // TODO: implement this.
    }
  }
}
</script>
