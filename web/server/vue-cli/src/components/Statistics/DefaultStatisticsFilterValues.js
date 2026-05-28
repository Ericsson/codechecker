import { useDetectionStatus } from "@/composables/useDetectionStatus";
import { DetectionStatus } from "@cc/report-server-types";

const detectionStatus = useDetectionStatus();

const defaultStatisticsFilterValues = {
  "is-unique": "on",
  "detection-status": [
    detectionStatus.detectionStatusFromCodeToString(DetectionStatus.NEW),
    detectionStatus.detectionStatusFromCodeToString(DetectionStatus.REOPENED),
    detectionStatus.detectionStatusFromCodeToString(DetectionStatus.UNRESOLVED)
  ]
};

export default defaultStatisticsFilterValues;
