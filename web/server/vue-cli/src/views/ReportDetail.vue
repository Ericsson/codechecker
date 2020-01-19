<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <report-tree
        :report="report"
      />
    </pane>
    <pane>
      <report
        :report="report"
      />
    </pane>
  </splitpanes>
</template>

<script>
import { Splitpanes, Pane } from 'splitpanes';

import { ccService } from '@cc-api';

import Report from '@/components/Report';
import ReportTree from '@/components/ReportTree/ReportTree';

export default {
  name: 'ReportDetail',
  components: {
    Splitpanes, Pane,
    Report,
    ReportTree
  },
  data() {
    return {
      report: null
    };
  },
  mounted() {
    const reportId = this.$router.currentRoute.query["reportId"] || 1;
    this.loadReport(reportId);
  },
  methods: {
    loadReport(reportId) {
      ccService.getClient().getReport(reportId, (err, reportData) => {
        this.report = reportData;
      });
    }
  }
}
</script>
