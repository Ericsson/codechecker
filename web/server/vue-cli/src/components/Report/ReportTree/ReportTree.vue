<template>
  <v-treeview
    v-model:opened="openedItems"
    v-model:activated="activeItems"
    v-model="tree"
    :items="items"
    :load-children="getChildren"
    return-object
    activatable
    item-value="id"
    open-on-click
    density="compact"
    @update:activated="onClick"
  >
    <template v-slot:prepend="{ item }">
      <span
        v-for="i in (0, item.level)"
        :key="i"
        class="v-treeview-item__level"
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

    <template v-slot:title="{ item }">
      <report-tree-label
        :item="item"
        :style="{ backgroundColor: item.bgColor, display: 'inline-block' }"
      />
    </template>
  </v-treeview>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import {
  DetectionStatus,
  MAX_QUERY_SIZE,
  Order,
  ReportFilter,
  ReviewStatus,
  SortMode,
  SortType
} from "@cc/report-server-types";
import { nextTick, onMounted, ref, watch } from "vue";

import { ReviewStatusIcon } from "@/components/Icons";

import formatReportDetails from "./ReportDetailFormatter";
import ReportTreeIcon from "./ReportTreeIcon";
import ReportTreeKind from "./ReportTreeKind";
import ReportTreeLabel from "./ReportTreeLabel";
import ReportTreeRootItem from "./ReportTreeRootItem";

const props = defineProps({
  report: { type: Object, default: null },
  reviewStatus: { type: Number, default: null }
});

const emit = defineEmits([ "click" ]);

const items = ref([]);
const tree = ref([]);
const openedItems = ref([]);
const activeItems = ref([]);
const runId = ref(null);
const fileId = ref(null);

watch(() => props.report, function() {
  if (isTheReportFileChanged()) {
    fetchReports();
  }
});

watch(() => props.reviewStatus, function() {
  if (!isTheReportFileChanged()) {
    fetchReports();
  }
});

onMounted(function() {
  if (props.report) {
    fetchReports();
  }
});

function removeEmptyRootElements() {
  if (items.value && items.value.length) {
    let _i = items.value.length;
    while (_i--) {
      let _j = items.value[_i].children.length;
      while (_j--) {
        if (!items.value[_i].children[_j].children.length) {
          items.value[_i].children.splice(_j, 1);
        }
      }
      if (!items.value[_i].children.length){
        items.value.splice(_i, 1);
      }
    }
  }
}

function fetchReports() {
  runId.value = props.report.runId;
  fileId.value = props.report.fileId;

  items.value = JSON.parse(JSON.stringify(ReportTreeRootItem));

  const _runIds = [ props.report.runId.toNumber() ];
  const _limit = MAX_QUERY_SIZE.toNumber();
  const _offset = 0;
  const _sortType = new SortMode({
    type: SortType.BUG_PATH_LENGTH,
    ord: Order.ASC
  });

  const _reportFilter = new ReportFilter({
    filepath: [ props.report.checkedFile ]
  });

  const _cmpData = null;
  const _getDetails = false;

  ccService.getClient().getRunResults(
    _runIds,
    _limit,
    _offset,
    _sortType,
    _reportFilter,
    _cmpData,
    _getDetails,
    handleThriftError(reports => {
      if (reports.length === MAX_QUERY_SIZE) {
        const _currentReport =
          reports.find(r => r.reportId.equals(props.report.reportId));
        if (!_currentReport) {
          reports.push(props.report);
        }
      }

      reports.sort((r1, r2) => {
        return r1.line - r2.line;
      }).forEach(report => {
        const _isResolved =
        report.detectionStatus === DetectionStatus.RESOLVED;

        const _status = !(
          _isResolved ||
          report.detectionStatus === DetectionStatus.OFF ||
          report.detectionStatus === DetectionStatus.UNAVAILABLE ||
          report.reviewData.status === ReviewStatus.FALSE_POSITIVE ||
          report.reviewData.status === ReviewStatus.INTENTIONAL
        ) ? items.value.find(item => item.isOutstanding)
          : items.value.find(item => !item.isOutstanding);

        const _parent = _status.children.find(item => {
          return _isResolved 
            ? item.detectionStatus === DetectionStatus.RESOLVED
            : item.severity === report.severity
          ;
        });

        if (_parent){
          _parent.children.push({
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

                    if (props.report.reportId.equals(item.report.reportId)) {
                      const _bugItem = item.children.find(c =>
                        c.id === `${report.reportId}_${ReportTreeKind.BUG}`
                      );

                      activeItems.value.push(_bugItem);
                    }
                  }));
              });
            }
          });
        }
      });
      openReportItems();

      removeEmptyRootElements();
    }));
}

function getChildren(item) {
  if (item.getChildren) {
    if (item.isLoading) return;

    item.isLoading = true;
    return item.getChildren(item);
  }
  return item.children;
}

function openReportItems() {
  const _isResolved =
    props.report.detectionStatus === DetectionStatus.RESOLVED;

  const _status = !(
    _isResolved ||
    props.report.detectionStatus === DetectionStatus.OFF ||
    props.report.detectionStatus === DetectionStatus.UNAVAILABLE ||
    props.report.reviewData.status === ReviewStatus.FALSE_POSITIVE ||
    props.report.reviewData.status === ReviewStatus.INTENTIONAL
  ) ? items.value.find(item => item.isOutstanding)
    : items.value.find(item => !item.isOutstanding);

  openedItems.value.push(_status);

  const _rootNode = _status.children.find(item => {
    return _isResolved 
      ? item.detectionStatus === DetectionStatus.RESOLVED
      : item.severity === props.report.severity;
  });

  if (_rootNode) {
    openedItems.value.push(_rootNode);

    const _reportNode = _rootNode.children.find(item => {
      return item.id === ReportTreeKind.getId(
        ReportTreeKind.REPORT, props.report
      );
    });

    if (_reportNode && _reportNode.getChildren && !_reportNode.isLoading) {
      _reportNode.isLoading = true;
      _reportNode.getChildren(_reportNode).then(() => {
        nextTick(() => {
          openedItems.value.push(_reportNode);
          const _node = document.querySelector(`[data-id='${_reportNode.id}']`);
          if (_node) {
            _node.scrollIntoView();
          }
        });
      });
    } else if (_reportNode) {
      nextTick(() => {
        openedItems.value.push(_reportNode);
        const _node = document.querySelector(`[data-id='${_reportNode.id}']`);
        if (_node) {
          _node.scrollIntoView();
        }
      });
    }
  }
}

function onClick(activeItemsParam) {
  emit("click", activeItemsParam[0]);
}

function isTheReportFileChanged() {
  if (runId.value && runId.value.equals(props.report.runId) &&
      fileId.value && fileId.value.equals(props.report.fileId)
  ) {
    return false;
  }
  else {
    return true;
  }
}
</script>

<style lang="scss" scoped>
:deep(.v-treeview-item) {
  min-height: 25px;
}

:deep(.v-treeview-item__level) {
  width: 18px;
}
</style>
