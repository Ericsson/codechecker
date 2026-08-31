import { ReviewStatus } from "@cc/report-server-types";

export function useReviewStatus() {
  function reviewStatusFromCodeToString(reviewCode) {
    switch (reviewCode) {
    case ReviewStatus.UNREVIEWED:
      return "Unreviewed";
    case ReviewStatus.CONFIRMED:
      return "Confirmed bug";
    case ReviewStatus.FALSE_POSITIVE:
      return "False positive";
    case ReviewStatus.INTENTIONAL:
      return "Intentional";
    default:
      return "";
    }
  }

  function reviewStatusFromStringToCode(status) {
    switch (status.toLowerCase()) {
    case "unreviewed":
      return ReviewStatus.UNREVIEWED;
    case "confirmed bug":
      return ReviewStatus.CONFIRMED;
    case "false positive":
      return ReviewStatus.FALSE_POSITIVE;
    case "intentional":
      return ReviewStatus.INTENTIONAL;
    default:
      return -1;
    }
  }

  function reviewStatusColor(reviewCode) {
    switch (reviewCode) {
    case ReviewStatus.UNREVIEWED: return "#4b9fd5";
    case ReviewStatus.CONFIRMED: return "#e92625";
    case ReviewStatus.FALSE_POSITIVE: return "#808080";
    case ReviewStatus.INTENTIONAL: return "#669603";
    default: return undefined;
    }
  }

  return {
    reviewStatusFromCodeToString,
    reviewStatusFromStringToCode,
    reviewStatusColor
  };
}
