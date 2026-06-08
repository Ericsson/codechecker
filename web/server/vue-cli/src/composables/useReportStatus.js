import { ReportStatus } from "@cc/report-server-types";

export function useReportStatus() {
  function reportStatusFromCodeToString(reportCode) {
    switch (reportCode) {
    case ReportStatus.OUTSTANDING:
      return "Outstanding";
    case ReportStatus.CLOSED:
      return "Closed";
    default:
      return "";
    }
  }

  function reportStatusFromStringToCode(status) {
    switch (status.toLowerCase()) {
    case "outstanding":
      return ReportStatus.OUTSTANDING;
    case "closed":
      return ReportStatus.CLOSED;
    default:
      return -1;
    }
  }

  return {
    reportStatusFromCodeToString,
    reportStatusFromStringToCode
  };
}
