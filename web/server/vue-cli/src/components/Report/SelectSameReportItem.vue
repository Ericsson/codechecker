<template>
  <div>
    <v-avatar left>
      <detection-status-icon :status="item.detectionStatus" />
    </v-avatar>
    {{ item.runName }}:{{ item.fileName }}:L{{ item.line }}
    <v-chip
      :color="getBugPathLenColor(item.bugPathLength)"
      label
      light
      small
    >
      {{ item.bugPathLength }}
    </v-chip>
  </div>
</template>

<script>
import { DetectionStatusIcon } from "@/components/Icons";
import { BugPathLengthColorMixin } from "@/mixins";

export default {
  name: "SelectSameReportItem",
  components: {
    DetectionStatusIcon
  },
  mixins: [ BugPathLengthColorMixin ],
  props: {
    item: { type: Object, required: true }
  }
}
</script>
