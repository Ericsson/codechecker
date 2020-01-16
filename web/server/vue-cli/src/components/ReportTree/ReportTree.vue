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
import {
  DetectionStatus,
  ExtendedReportDataType
} from '@cc/report-server-types';

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
                  item.children = this.formatReportDetails(report, details);
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

    formatReportDetails(report, reportDetails) {
      const items = [];

      // Add extended items such as notes and macros.
      const extendedItems = this.formatExtendedData(report,
        reportDetails.extendedData);
      items.push(...extendedItems);

      // Add main report node.
      items.push({
        id : `${report.reportId}_${ReportTreeKind.BUG}`,
        name: report.checkerMsg,
        kind: ReportTreeKind.BUG
      });

      return items;
    },

    formatExtendedData(report, extendedData) {
      const items = [];

      // Add macro expansions.
      const macros = extendedData.filter((data) => {
        return data.type === ExtendedReportDataType.MACRO;
      });

      if (macros.length) {
        const id = `${report.reportId}_${ReportTreeKind.MACRO_EXPANSION}`;
        const children = this.formatExtendedReportDataChildren(macros,
          ReportTreeKind.MACRO_EXPANSION_ITEM, id)

        items.push({
          id: id,
          name: "Macro expansions",
          kind: ReportTreeKind.MACRO_EXPANSION,
          children: children
        })
      }

      // Add notes.
      const notes = extendedData.filter((data) => {
        return data.type === ExtendedReportDataType.NOTE;
      });

      if (notes.length) {
        const id = `${report.reportId}_${ReportTreeKind.NOTE}`;
        const children = this.formatExtendedReportDataChildren(notes,
          ReportTreeKind.NOTE_ITEM, id)

        items.push({
          id: id,
          name: "Notes",
          kind: ReportTreeKind.NOTE,
          children: children
        })
      }

      return items;
    },

    formatExtendedReportDataChildren(extendedData, kind, parentId) {
      return extendedData.sort((a, b) => {
        return a.startLine - b.startLine;
      }).map((data, index) => {
        return {
          id: `${parentId}_${index}`,
          name: data.message,
          kind: kind,
          data: data
        };
      });
    }
  }
}
</script>
