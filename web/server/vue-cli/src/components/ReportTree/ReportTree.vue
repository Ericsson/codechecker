<template>
  <v-treeview
    v-model="tree"
    :items="items"
    :load-children="getChildren"
    :return-object="true"
    activatable
    item-key="id"
    open-on-click
    dense
    @update:active="onClick"
  >
    <template v-slot:prepend="{ item }">
      <span
        v-for="i in (0, item.level)"
        :key="i"
        class="v-treeview-node__level"
        :style="{ display: 'inline-block' }"
      >
        &nbsp;
      </span>

      <report-tree-icon :item="item" />
    </template>

    <template v-slot:label="{ item }">
      <report-tree-label
        :item="item"
        :style="{ backgroundColor: item.bgColor, display: 'inline-block' }"
      />
    </template>
  </v-treeview>
</template>

<script>
import VTreeview from "Vuetify/VTreeview/VTreeview";

import { ccService } from '@cc-api';
import { DetectionStatus, ReportFilter } from '@cc/report-server-types';

import ReportTreeIcon from './ReportTreeIcon';
import ReportTreeLabel from './ReportTreeLabel';
import ReportTreeKind from './ReportTreeKind';
import ReportTreeRootItem from './ReportTreeRootItem';
import formatReportDetails from './ReportDetailFormatter';

export default {
  name: 'ReportTree',
  components: {
    VTreeview,
    ReportTreeIcon,
    ReportTreeLabel
  },

  props: {
    report: { type: Object, default: null }
  },

  data() {
    return {
      ReportTreeKind,
      root: {},
      items: [],
      tree: []
    };
  },

  watch: {
    report() {
      this.fetchReports();
    }
  },

  methods: {
    // Remove root elements which do not have any children.
    removeEmptyRootElements() {
      let i = this.items.length;
      while (i--) {
        if (!this.items[i].children.length) {
          this.items.splice(i, 1);
        }
      }
    },

    fetchReports() {
      this.items = JSON.parse(JSON.stringify(ReportTreeRootItem));



      const runIds = [ this.report.runId ];
      const limit = null;
      const offset = null;
      const sortType = null;

      const reportFilter = new ReportFilter({
        filepath: [ this.report.checkedFile ]
      });

      const cmpData = null;
      const getDetails = false;

      ccService.getClient().getRunResults(runIds, limit, offset, sortType,
      reportFilter, cmpData, getDetails, (err, reports) => {
        reports.forEach((report) => {
          const isResolved =
            report.detectionStatus === DetectionStatus.RESOLVED;

          const parent = this.items.find((item) => {
            return isResolved
              ? item.detectionStatus === DetectionStatus.RESOLVED
              : item.severity === report.severity;
          });

          parent.children.push({
            id: report.reportId.toString(),
            name: report.checkerId,
            kind: ReportTreeKind.REPORT,
            report: report,
            children: [],
            getChildren: (item) => {
              return new Promise((resolve) => {
                ccService.getClient().getReportDetails(report.reportId,
                (err, details) => {
                  item.children = formatReportDetails(report, details);
                  resolve();
                });
              });
            }
          });
        });

        this.removeEmptyRootElements();
      });
    },

    getChildren(item) {
      if (item.getChildren) {
        return item.getChildren(item);
      }
      return item.children;
    },

    onClick(/* activeItems */) {
      /* const item = activeItems[0]; */
    }
  }
}
</script>
