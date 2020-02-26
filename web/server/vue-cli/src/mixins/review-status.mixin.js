import { ReviewStatus } from "@cc/report-server-types";

export default {
  methods: {
    reviewStatusFromCodeToString(reviewCode) {
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
    },
  
    reviewStatusFromStringToCode(status) {
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
  }
};
