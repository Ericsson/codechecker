<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <report-filter
        v-fill-height
        :namespace="namespace"
        :show-newcheck="false"
        :show-review-status="false"
        :show-remove-filtered-reports="false"
        :report-count="reportCount"
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
import { Pane, Splitpanes } from "splitpanes";
import { mapState } from "vuex";

import { ccService, handleThriftError } from "@cc-api";

import {
  CheckerStatistics,
  SeverityStatistics
} from "@/components/Statistics";
import { FillHeight } from "@/directives";
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
      namespace: namespace,
      reportCount: 0
    };
  },

  computed: {
    ...mapState({
      runIds(state, getters) {
        return getters[`${this.namespace}/getRunIds`];
      },
      reportFilter(state, getters) {
        return getters[`${this.namespace}/getReportFilter`];
      }
    })
  },

  methods: {
    refresh() {
      ccService.getClient().getRunResultCount(this.runIds,
        this.reportFilter, null, handleThriftError(res => {
          this.reportCount = res.toNumber();
        }));

      const statistics = this.$refs.statistics;
      statistics.forEach(statistic => statistic.fetchStatistics());
    }
  }
};
</script>

<style lang="scss" scoped>
.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}
</style>
