<template>
  <v-treeview
    v-model="tree"
    :items="items"
    :load-children="getChildren"
    :return-object="true"
    activatable
    item-key="id"
    open-on-click
  >
    <template v-slot:prepend="{ item }">
      <report-tree-icon :item="item" />
    </template>

    <template v-slot:label="{ item }">
      <report-tree-label :item="item" />
    </template>
  </v-treeview>
</template>

<script>
import VTreeview from "Vuetify/VTreeview/VTreeview";

import { ccService } from '@cc-api';

import ReportTreeIcon from './ReportTreeIcon';
import ReportTreeLabel from './ReportTreeLabel';
import ReportTreeKind from './ReportTreeKind';
import ReportTreeRootItem from './ReportTreeRootItem';

export default {
  name: 'ReportTree',
  components: {
    VTreeview,
    ReportTreeIcon,
    ReportTreeLabel
  },

  data() {
    return {
      ReportTreeKind,
      root: {},
      items: [],
      tree: []
    };
  },

  mounted() {
    this.fetchReports();
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

      const runIds = null;
      const limit = null;
      const offset = null;
      const sortType = null;
      const reportFilter = null;
      const cmpData = null;
      const getDetails = false;

      const parent = this.items.find((item) => item.id == 'high');

      ccService.getClient().getRunResults(runIds, limit, offset, sortType,
      reportFilter, cmpData, getDetails, (err, reports) => {
        reports.forEach((report) => {
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
                  this.addReportDetails(report, details, item.children);
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

    addReportDetails(report, reportDetails, children) {
      children.push({
        id : report.reportId.toString() + '_main',
        name: report.checkerMsg,
        kind: ReportTreeKind.BUG
      });
    }
  }
}
</script>
