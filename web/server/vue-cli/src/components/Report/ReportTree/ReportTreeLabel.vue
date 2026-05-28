<template>
  <span :data-id="item.id">
    <span v-if="item.kind === ReportTreeKind.REPORT">
      L{{ item.report.line }} &ndash; {{ item.report.checkerId }}
      [{{ item.report.bugPathLength }}]
    </span>

    <span
      v-else-if="item.kind === ReportTreeKind.REPORT_STEPS"
      :title="reportStepContent"
    >
      {{ reportStepContent }}
    </span>

    <span v-else-if="item.kind === ReportTreeKind.BUG">
      <b><u>{{ item.name }}</u></b>
    </span>

    <span v-else-if="isExtendedReportData">
      <b>{{ item.name }}</b>
    </span>

    <span v-else-if="isExtendedReportDataItem">
      L{{ item.data.startLine }} &ndash; {{ item.name }}
    </span>
    <span v-else-if="item.kind === ReportTreeKind.SEVERITY_LEVEL">
      {{ item.name }}
      <span v-if="newReportCount" style="color: #ec7672;">
        {{ newReportCountLabel }}
      </span>
    </span>
    <span v-else>
      {{ item.name }}
    </span>
  </span>
</template>

<script setup>
import { DetectionStatus } from "@cc/report-server-types";
import { computed } from "vue";
import ReportTreeKind from "./ReportTreeKind";

const props = defineProps({
  item: { type: Object, required: true }
});

const reportStepContent = computed(function() {
  return `${fileName.value}${props.item.step.startLine} ` +
    `- ${props.item.step.msg}`;
});

const fileName = computed(function() {
  return props.item.fileName ? `${props.item.fileName}:` : "L";
});

const isExtendedReportData = computed(function() {
  return props.item.kind === ReportTreeKind.MACRO_EXPANSION ||
         props.item.kind === ReportTreeKind.NOTE;
});

const isExtendedReportDataItem = computed(function() {
  return props.item.kind === ReportTreeKind.MACRO_EXPANSION_ITEM ||
         props.item.kind === ReportTreeKind.NOTE_ITEM;
});

const newReportCount = computed(function() {
  if (props.item && props.item.kind === ReportTreeKind.SEVERITY_LEVEL) {
    return props.item.children.filter(element => {
      return element.report.detectionStatus == DetectionStatus.NEW;
    }).length;
  }
  return 0;
});

const newReportCountLabel = computed(function() {
  return ` [${newReportCount.value} new]`;
});
</script>
