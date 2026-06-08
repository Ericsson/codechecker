import { ReportStatus } from "@cc/report-server-types";

export default {
  methods: {
    reportStatusFromCodeToString(reportCode) {
      switch (reportCode) {
      case ReportStatus.OUTSTANDING:
        return "Outstanding";
      case ReportStatus.CLOSED:
        return "Closed";
      default:
        return "";
      }
    },
  
    reportStatusFromStringToCode(status) {
      switch (status.toLowerCase()) {
      case "outstanding":
        return ReportStatus.OUTSTANDING;
      case "closed":
        return ReportStatus.CLOSED;
      default:
        return -1;
      }
    }
  }
};
