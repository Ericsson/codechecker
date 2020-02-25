<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <report-filter
        v-fill-height
        :namespace="namespace"
        :show-newcheck="false"
        :show-review-status="false"
        :show-remove-filtered-reports="false"
        @refresh="refresh"
      />
    </pane>
    <pane>
      <div v-fill-height>
        <!--
          'refs' becomes an Array if used inside a v-for. This is the reason
          why we use this.
        -->
        <span
          v-for="i in 1"
          :key="i"
        >
          <checker-statistics
            ref="statistics"
            :namespace="namespace"
          />

          <severity-statistics
            ref="statistics"
            :namespace="namespace"
          />
        </span>
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
    refresh() {
      const statistics = this.$refs.statistics;
      statistics.forEach(statistic => statistic.fetchStatistics());
    }
  }
};
</script>
