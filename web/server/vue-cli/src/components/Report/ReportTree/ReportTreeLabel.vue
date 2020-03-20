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

    <span v-else>
      {{ item.name }}
    </span>
  </span>
</template>

<script>
import ReportTreeKind from "./ReportTreeKind";

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
      ReportTreeKind
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
    }
  }
};
</script>
