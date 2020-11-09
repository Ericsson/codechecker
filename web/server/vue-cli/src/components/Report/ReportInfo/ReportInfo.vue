<template>
  <v-container>
    <v-row
      v-for="key in fields"
      :key="key"
    >
      <v-col class="pt-0" cols="4" align-self="center">
        <strong>{{ formatLabel(key) }}:</strong>
      </v-col>
      <v-col class="pt-0">
        <component
          :is="links[key] ? 'router-link' : 'span'"
          :class="key"
          v-bind="{ to: links[key] }"
        >
          <severity-icon
            v-if="key === 'severity'"
            :status="value[key]"
          />

          <detection-status-icon
            v-else-if="key === 'detectionStatus'"
            :status="value[key]"
          />

          <review-status-icon
            v-else-if="key === 'reviewData'"
            :status="value[key].status"
          />

          <span v-else-if="key === 'fixedAt'">
            <span v-if="value[key]">{{ value[key] }}</span>
            <span v-else>-</span>
          </span>

          <span v-else-if="key === 'runName'">
            {{ runName }}
          </span>

          <v-chip
            v-else-if="key === 'bugPathLength'"
            :color="getBugPathLenColor(value[key])"
          >
            {{ value[key] }}
          </v-chip>

          <span v-else>
            {{ value[key] }}
          </span>
        </component>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ccService } from "@cc-api";
import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";
import {
  BugPathLengthColorMixin,
  DetectionStatusMixin,
  ReviewStatusMixin,
  SeverityMixin
} from "@/mixins";

export default {
  name: "ReportInfo",
  components: {
    DetectionStatusIcon,
    ReviewStatusIcon,
    SeverityIcon
  },
  mixins: [
    BugPathLengthColorMixin,
    DetectionStatusMixin,
    ReviewStatusMixin,
    SeverityMixin
  ],
  props: {
    value: { type: Object, default: null }
  },
  data() {
    return {
      runName: null
    };
  },
  computed: {
    fields() {
      return [
        "runName", "reportId", "bugHash", "checkedFile", "line",
        "column", "analyzerName", "checkerId", "checkerMsg", "bugPathLength",
        "severity", "detectionStatus", "reviewData", "detectedAt", "fixedAt"
      ];
    },
    links() {
      return {
        "runName": { name: "runs", query: {
          "name": this.runName } },
        "bugHash": { name: "reports", query: {
          "report-hash": this.value.bugHash } },
        "checkedFile": { name: "reports", query: {
          "filepath": this.value.checkedFile } },
        "analyzerName": { name: "reports", query: {
          "analyzer-name": this.value.analyzerName } },
        "checkerId": { name: "reports", query: {
          "checker-name": this.value.checkerId } },
        "checkerMsg": { name: "reports", query: {
          "checker-msg": this.value.checkerMsg } },
        "severity": { name: "reports", query: {
          "severity": this.severityFromCodeToString(this.value.severity) } },
        "detectionStatus": { name: "reports", query: {
          "detection-status": this.detectionStatusFromCodeToString(
            this.value.detectionStatus) } },
        "reviewData": { name: "reports", query: {
          "review-status": this.reviewStatusFromCodeToString(
            this.value.reviewData.status) } },
        "bugPathLength": { name: "reports", query: {
          "min-bug-path-length": this.value.bugPathLength,
          "max-bug-path-length": this.value.bugPathLength } },
      };
    }
  },
  watch: {
    async value() {
      this.fetchRunName();
    }
  },
  mounted() {
    this.fetchRunName();
  },
  methods: {
    async fetchRunName() {
      const runs = await ccService.getRuns([ this.value.runId ]);
      this.runName = runs[0].name;
    },

    formatLabel(key) {
      switch (key) {
      case "runName":
        return "Run name";
      case "reportId":
        return "Report id";
      case "bugHash":
        return "Report hash";
      case "checkedFile":
        return "File path";
      case "line":
        return "Line";
      case "column":
        return "Column";
      case "checkerId":
        return "Checker name";
      case "checkerMsg":
        return "Checker message";
      case "analyzerName":
        return "Analyzer name";
      case "bugPathLength":
        return "Bug path length";
      case "severity":
        return "Severity";
      case "detectionStatus":
        return "Latest detection status";
      case "reviewData":
        return "Latest review status";
      case "detectedAt":
        return "Detected at";
      case "fixedAt":
        return "Fixed at";
      default:
        return key;
      }
    }
  }
};
</script>

<style lang="scss" scoped>
a {
  &.severity,
  &.detectionStatus,
  &.reviewData,
  &.bugPathLength {
    text-decoration: none;
  }

  &.bugPathLength .v-chip {
    cursor: pointer;
  }
}
</style>
