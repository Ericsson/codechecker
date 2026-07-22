<template>
  <v-row class="ga-2">
    <v-col class="d-flex flex-column">
      <v-card
        class="pa-2 rounded-lg mb-2 d-flex flex-column fill-height bg-grey-card"
        variant="flat"
      >
        <v-card-title class="text-body-1 text-uppercase">
          Run & Report Information
        </v-card-title>
        <v-card-text>
          <v-col>
            <v-row>
              <report-info-item
                :title="formatLabel('runName')"
                :value="runName"
                :query="links['runName']"
              />
            </v-row>
            <v-row>
              <report-info-item
                :title="formatLabel('reportId')"
                :value="value['reportId']"
              />
            </v-row>
            <v-row>
              <report-info-item
                :title="formatLabel('bugHash')"
                :value="value['bugHash']"
                :query="links['bugHash']"
              />
            </v-row>
          </v-col>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col class="d-flex flex-column">
      <v-card
        class="pa-2 rounded-lg mb-2 d-flex flex-column fill-height bg-grey-card"
        variant="flat"
      >
        <v-card-title class="text-body-1 text-uppercase">
          Analyzer & Checker Information
        </v-card-title>
        <v-card-text>
          <v-col>
            <v-row>
              <report-info-item
                :title="formatLabel('analyzerName')"
                :value="value['analyzerName']"
                :query="links['analyzerName']"
              />
            </v-row>
            <v-row>
              <report-info-item
                :title="formatLabel('checkerId')"
                :value="value['checkerId']"
                :query="links['checkerId']"
                :doc-url="docUrl"
              />
            </v-row>
            <v-row>
              <report-info-item
                :title="formatLabel('checkerMsg')"
                :value="value['checkerMsg']"
                :query="links['checkerMsg']"
              />
            </v-row>
          </v-col>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
  <v-card
    class="pa-2 rounded-lg mb-2 bg-grey-card"
    variant="flat"
  >
    <v-card-title class="text-body-1 text-uppercase">
      File & Location
    </v-card-title>
    <v-card-text>
      <v-row>
        <v-col>
          <report-info-item
            :title="formatLabel('checkedFile')"
            :value="value['checkedFile']"
            :query="links['checkedFile']"
          />
        </v-col>
        <v-col>
          <report-info-item
            :title="formatLabel('line')"
            :value="value['line']"
          />
        </v-col>
        <v-col>
          <report-info-item
            :title="formatLabel('column')"
            :value="value['column']"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
  <v-row class="ga-2">
    <v-col class="d-flex flex-column">
      <v-card
        class="pa-2 rounded-lg mb-2 d-flex flex-column fill-height bg-grey-card"
        variant="flat"
      >
        <v-card-title class="text-body-1 text-uppercase">
          Bug Path Length & Severity Information
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col>
              <report-info-item
                :title="formatLabel('bugPathLength')"
                :value="value['bugPathLength']"
                :query="links['bugPathLength']"
                chip
              />
            </v-col>
            <v-col>
              <report-info-item
                :title="formatLabel('severity')"
                :value="value['severity']"
                :query="links['severity']"
                icon-shown
              >
                <template #icon>
                  <severity-icon
                    :status="value['severity']"
                  />
                </template>
              </report-info-item>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col class="d-flex flex-column">
      <v-card
        class="pa-2 rounded-lg mb-2 d-flex flex-column fill-height bg-grey-card"
        variant="flat"
      >
        <v-card-title class="text-body-1 text-uppercase">
          Detection & Review Status
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col>
              <report-info-item
                :title="formatLabel('detectionStatus')"
                :value="value['detectionStatus']"
                :query="links['detectionStatus']"
                icon-shown
              >
                <template #icon>
                  <detection-status-icon
                    :status="value['detectionStatus']"
                  />
                </template>
              </report-info-item>
            </v-col>
            <v-col>
              <report-info-item
                :title="formatLabel('reviewData')"
                :value="value['reviewData']"
                :query="links['reviewData']"
                icon-shown
              >
                <template #icon>
                  <review-status-icon
                    :status="value['reviewData'].status"
                  />
                </template>
              </report-info-item>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
  <v-card
    class="pa-2 rounded-lg mb-2 bg-grey-card"
    variant="flat"
  >
    <v-card-title class="text-body-1 text-uppercase">
      Detection & Fix Date
    </v-card-title>
    <v-card-text>
      <v-row>
        <v-col>
          <report-info-item
            :title="formatLabel('detectedAt')"
            :value="value['detectedAt']"
          />
        </v-col>
        <v-col>
          <report-info-item
            :title="formatLabel('fixedAt')"
            :value="value['fixedAt']"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";
import { useDetectionStatus } from "@/composables/useDetectionStatus";
import { useReviewStatus } from "@/composables/useReviewStatus";
import { useSeverity } from "@/composables/useSeverity";
import { ccService, handleThriftError } from "@cc-api";
import ReportInfoItem from "@/components/Report/ReportInfo/ReportInfoItem";
import { Checker } from "@cc/report-server-types";

const props = defineProps({
  value: { type: Object, default: null }
});

const runName = ref(null);

const detectionStatus = useDetectionStatus();
const reviewStatus = useReviewStatus();
const severity = useSeverity();

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

const docUrl = ref(null);

watch(() => props.value, function() {
  fetchRunName();
  fetchDocUrl();
});

onMounted(function() {
  fetchRunName();
  fetchDocUrl();
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

async function fetchDocUrl() {
  const checker = new Checker({
    analyzerName: props.value.analyzerName,
    checkerId: props.value.checkerId
  });

  await new Promise(resolve => {
    ccService.getClient().getCheckerLabels(
      [ checker ],
      handleThriftError(labels => {
        const docUrlLabels = labels[0].filter(
          param => param.startsWith("doc_url")
        );
        docUrl.value = docUrlLabels.length ?
          docUrlLabels[0].split("doc_url:")[1] : null;
        resolve(docUrl.value);
      })
    );
  });
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
