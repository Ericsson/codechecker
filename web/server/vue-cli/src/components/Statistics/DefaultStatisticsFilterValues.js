import { DetectionStatus } from "@cc/report-server-types";
import { DetectionStatusMixin } from "@/mixins";

const detectionStatusToString =
DetectionStatusMixin.methods.detectionStatusFromCodeToString;

const defaultStatisticsFilterValues = {
  "is-unique": "on",
  "detection-status": [
    detectionStatusToString(DetectionStatus.NEW),
    detectionStatusToString(DetectionStatus.REOPENED),
    detectionStatusToString(DetectionStatus.UNRESOLVED)
  ]
};

export default defaultStatisticsFilterValues;
