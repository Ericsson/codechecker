import { DetectionStatus } from "@cc/report-server-types";

export default {
  methods: {
    detectionStatusFromCodeToString(status) {
      switch (parseInt(status)) {
      case DetectionStatus.NEW:
        return "New";
      case DetectionStatus.RESOLVED:
        return "Resolved";
      case DetectionStatus.UNRESOLVED:
        return "Unresolved";
      case DetectionStatus.REOPENED:
        return "Reopened";
      case DetectionStatus.OFF:
        return "Off";
      case DetectionStatus.UNAVAILABLE:
        return "Unavailable";
      default:
        return "";
      }
    },

    detectionStatusFromStringToCode(status) {
      switch (status.toLowerCase()) {
      case "new":
        return DetectionStatus.NEW;
      case "resolved":
        return DetectionStatus.RESOLVED;
      case "unresolved":
        return DetectionStatus.UNRESOLVED;
      case "reopened":
        return DetectionStatus.REOPENED;
      case "off":
        return DetectionStatus.OFF;
      case "unavailable":
        return DetectionStatus.UNAVAILABLE;
      default:
        return -1;
      }
    }
  }
};
