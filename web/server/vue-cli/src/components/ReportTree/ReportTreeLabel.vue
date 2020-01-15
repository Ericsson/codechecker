<template>
  <span v-if="item.kind === ReportTreeKind.REPORT">
    L{{ item.report.line }} &ndash; {{ item.report.checkerId }}
    [{{ item.report.bugPathLength }}]
  </span>

  <span v-else-if="item.kind === ReportTreeKind.REPORT_STEPS">
    L{{ item.report.line }} &ndash; {{ item.name }}
  </span>

  <span v-else>
    {{ item.name }}
  </span>
</template>

<script>
import ReportTreeKind from './ReportTreeKind';

export default {
  name: 'ReportTreeLabel',
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
}
</script>
