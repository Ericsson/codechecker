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
          v-bind="{ to: links[key] }"
          :is="links[key] ? 'router-link' : 'span'"
          :class="key"
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
            :color="bugPathLenColor.getBugPathLenColor(value[key])"
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

<script setup>
import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";
import { useBugPathLenColor } from "@/composables/useBugPathLenColor";
import { useDetectionStatus } from "@/composables/useDetectionStatus";
import { useReviewStatus } from "@/composables/useReviewStatus";
import { useSeverity } from "@/composables/useSeverity";
import { ccService } from "@cc-api";
import { computed, onMounted, ref, watch } from "vue";

const props = defineProps({
  value: { type: Object, default: null }
});

const runName = ref(null);

const bugPathLenColor = useBugPathLenColor();
const detectionStatus = useDetectionStatus();
const reviewStatus = useReviewStatus();
const severity = useSeverity();

const fields = computed(function() {
  return [
    "runName", "reportId", "bugHash", "checkedFile", "line",
    "column", "analyzerName", "checkerId", "checkerMsg", "bugPathLength",
    "severity", "detectionStatus", "reviewData", "detectedAt", "fixedAt"
  ];
});

const links = computed(function() {
  return {
    "runName": { name: "runs", query: {
      "run": runName.value } },
    "bugHash": { name: "reports", query: {
      "report-hash": props.value.bugHash } },
    "checkedFile": { name: "reports", query: {
      "filepath": props.value.checkedFile } },
    "analyzerName": { name: "reports", query: {
      "analyzer-name": props.value.analyzerName } },
    "checkerId": { name: "reports", query: {
      "checker-name": props.value.checkerId } },
    "checkerMsg": { name: "reports", query: {
      "checker-msg": props.value.checkerMsg } },
    "severity": { name: "reports", query: {
      "severity": severity.severityFromCodeToString(props.value.severity) } },
    "detectionStatus": { name: "reports", query: {
      "detection-status": detectionStatus.detectionStatusFromCodeToString(
        props.value.detectionStatus) } },
    "reviewData": { name: "reports", query: {
      "review-status": reviewStatus.reviewStatusFromCodeToString(
        props.value.reviewData.status) } },
    "bugPathLength": { name: "reports", query: {
      "min-bug-path-length": props.value.bugPathLength,
      "max-bug-path-length": props.value.bugPathLength } },
  };
});

watch(() => props.value, function() {
  fetchRunName();
});

onMounted(function() {
  fetchRunName();
});

async function fetchRunName() {
  const runs = await ccService.getRuns([ props.value.runId ]);
  runName.value = runs[0].name;
}

function formatLabel(key) {
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
