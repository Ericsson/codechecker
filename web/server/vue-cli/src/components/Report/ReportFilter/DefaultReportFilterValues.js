import { useDetectionStatus } from "@/composables/useDetectionStatus";
import { useReviewStatus } from "@/composables/useReviewStatus";
import { DetectionStatus, ReviewStatus } from "@cc/report-server-types";

const detectionStatus = useDetectionStatus();
const reviewStatus = useReviewStatus();

const defaultReportFilterValues = {
  "review-status": [
    reviewStatus.reviewStatusFromCodeToString(ReviewStatus.UNREVIEWED),
    reviewStatus.reviewStatusFromCodeToString(ReviewStatus.CONFIRMED)
  ],
  "detection-status": [
    detectionStatus.detectionStatusFromCodeToString(DetectionStatus.NEW),
    detectionStatus.detectionStatusFromCodeToString(DetectionStatus.REOPENED),
    detectionStatus.detectionStatusFromCodeToString(DetectionStatus.UNRESOLVED)
  ]
};

export default defaultReportFilterValues;