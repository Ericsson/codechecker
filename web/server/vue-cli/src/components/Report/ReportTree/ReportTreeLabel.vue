<template>
  <span :data-id="item.id">
    <span v-if="item.kind === ReportTreeKind.REPORT">
      L{{ item.report.line }} &ndash; {{ item.report.checkerId }}
      [{{ item.report.bugPathLength }}]
    </span>

    <span v-else-if="item.kind === ReportTreeKind.REPORT_STEPS">
      {{ fileName }}{{ item.step.startLine }} &ndash; {{ item.step.msg }}
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

<script>
import ReportTreeKind from "./ReportTreeKind";
import { DetectionStatus } from "@cc/report-server-types";

export default {
  name: "ReportTreeLabel",
  props: {
    item: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      ReportTreeKind,
      DetectionStatus
    };
  },
  computed: {
    fileName() {
      return this.item.shortFileName ? `${this.item.shortFileName}:` : "L";
    },

    isExtendedReportData() {
      return this.item.kind === ReportTreeKind.MACRO_EXPANSION ||
             this.item.kind === ReportTreeKind.NOTE;
    },
    isExtendedReportDataItem() {
      return this.item.kind === ReportTreeKind.MACRO_EXPANSION_ITEM ||
             this.item.kind === ReportTreeKind.NOTE_ITEM;
    },

    newReportCount() {
      if (this.item && this.item.kind === ReportTreeKind.SEVERITY_LEVEL) {
        return this.item.children.filter(element => {
          return element.report.detectionStatus == DetectionStatus.NEW;
        }).length;
      }
      return 0;
    },

    newReportCountLabel() {
      return ` [${this.newReportCount} new]`;
    }
  }
};
</script>
