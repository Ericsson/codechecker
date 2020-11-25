<template>
  <v-treeview
    v-model="tree"
    :items="items"
    :open.sync="openedItems"
    :active.sync="activeItems"
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

      <review-status-icon
        v-if="item.kind === ReportTreeKind.REPORT"
        :status="parseInt(item.report.reviewData.status)"
      />
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
import { ccService, handleThriftError } from "@cc-api";
import {
  DetectionStatus,
  MAX_QUERY_SIZE,
  ReportFilter
} from "@cc/report-server-types";

import { ReviewStatusIcon } from "@/components/Icons";

import ReportTreeIcon from "./ReportTreeIcon";
import ReportTreeLabel from "./ReportTreeLabel";
import ReportTreeKind from "./ReportTreeKind";
import ReportTreeRootItem from "./ReportTreeRootItem";
import formatReportDetails from "./ReportDetailFormatter";

export default {
  name: "ReportTree",
  components: {
    ReportTreeIcon,
    ReportTreeLabel,
    ReviewStatusIcon
  },

  props: {
    report: { type: Object, default: null }
  },

  data() {
    return {
      ReportTreeKind,
      root: {},
      items: [],
      tree: [],
      openedItems: [],
      activeItems: [],
      runId: null,
      fileId: null
    };
  },

  watch: {
    report() {
      this.fetchReports();
    }
  },

  mounted() {
    if (this.report) {
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
      // If the runId and the checkedFile are not changed, we should not load
      // the reports.
      if (this.runId && this.runId.equals(this.report.runId) &&
          this.fileId && this.fileId.equals(this.report.fileId)
      ) {
        return;
      }

      this.runId = this.report.runId;
      this.fileId = this.report.fileId;

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

      // TODO: handle the case when there are more than MAX_QUERY_SIZE reports
      // in the given file.
      ccService.getClient().getRunResults(runIds, limit, offset, sortType,
        reportFilter, cmpData, getDetails, handleThriftError(reports => {
          if (reports.length === MAX_QUERY_SIZE) {
            const currentReport =
              reports.find(r => r.reportId.equals(this.report.reportId));
            if (!currentReport) {
              reports.push(this.report);
            }
          }

          reports.sort((r1, r2) => {
            return r1.line - r2.line;
          }).forEach(report => {
            const isResolved =
            report.detectionStatus === DetectionStatus.RESOLVED;

            const parent = this.items.find(item => {
              return isResolved
                ? item.detectionStatus === DetectionStatus.RESOLVED
                : item.severity === report.severity;
            });

            parent.children.push({
              id: ReportTreeKind.getId(ReportTreeKind.REPORT, report),
              name: report.checkerId,
              kind: ReportTreeKind.REPORT,
              report: report,
              children: [],
              itemChildren: [],
              isLoading: false,
              getChildren: item => {
                return new Promise(resolve => {
                  ccService.getClient().getReportDetails(report.reportId,
                    handleThriftError(details => {
                      item.children = formatReportDetails(report, details);
                      resolve();

                      if (this.report.reportId.equals(item.report.reportId)) {
                        const bugItem = item.children.find(c =>
                          c.id === `${report.reportId}_${ReportTreeKind.BUG}`
                        );

                        this.activeItems.push(bugItem);
                      }
                    }));
                });
              }
            });
          });
          this.openReportItems();

          this.removeEmptyRootElements();
        }));
    },

    getChildren(item) {
      if (item.getChildren) {
        // There is a todo in the source code of vuetify that it will try to
        // load children every time if the response is empty.
        // See: vuetify/src/components/VTreeview/VTreeviewNode.ts#L158-L159
        // FIXME: if this problem will be solved, the isLoading property can
        // be removed.
        if (item.isLoading) return;

        item.isLoading = true;
        return item.getChildren(item);
      }
      return item.children;
    },

    openReportItems() {
      const isResolved =
        this.report.detectionStatus === DetectionStatus.RESOLVED;

      const rootNode = this.items.find(item => {
        return isResolved
          ? item.detectionStatus === DetectionStatus.RESOLVED
          : item.severity === this.report.severity;
      });

      this.openedItems.push(rootNode);
      this.$nextTick(() => {
        const reportNode = rootNode.children.find(item => {
          return item.id === this.report.reportId.toString();
        });

        if (reportNode) {
          const node = this.$el.querySelector(`[data-id='${reportNode.id}']`);
          if (node) {
            node.scrollIntoView();
          }
        }

        this.openedItems.push(reportNode);
      });
    },

    onClick(activeItems) {
      this.$emit("click", activeItems[0]);
    }
  }
};
</script>

<style lang="scss" scoped>
.v-treeview--dense ::v-deep .v-treeview-node__root {
  min-height: 25px;
}

::v-deep .v-treeview-node__level {
  width: 18px;
}
</style>
