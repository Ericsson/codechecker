import { DetectionStatus, ReviewStatus } from "@cc/report-server-types";
import { DetectionStatusMixin, ReviewStatusMixin } from "@/mixins";

const reviewStatusToString =
  ReviewStatusMixin.methods.reviewStatusFromCodeToString;

const detectionStatusToString =
DetectionStatusMixin.methods.detectionStatusFromCodeToString;

const defaultReportFilterValues = {
  "review-status": [
    reviewStatusToString(ReviewStatus.UNREVIEWED),
    reviewStatusToString(ReviewStatus.CONFIRMED)
  ],
  "detection-status": [
    detectionStatusToString(DetectionStatus.NEW),
    detectionStatusToString(DetectionStatus.REOPENED),
    detectionStatusToString(DetectionStatus.UNRESOLVED)
  ]
};

export default defaultReportFilterValues;