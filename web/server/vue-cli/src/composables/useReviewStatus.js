import { ReviewStatus } from "@cc/report-server-types";
import { getCssColor } from "@/utilities/colors";

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
    case ReviewStatus.UNREVIEWED: return getCssColor("color-soft-blue");
    case ReviewStatus.CONFIRMED: return getCssColor("color-soft-red");
    case ReviewStatus.FALSE_POSITIVE: return getCssColor("color-gray");
    case ReviewStatus.INTENTIONAL: return getCssColor("color-soft-green");
    default: return undefined;
    }
  }

  return {
    reviewStatusFromCodeToString,
    reviewStatusFromStringToCode,
    reviewStatusColor
  };
}
