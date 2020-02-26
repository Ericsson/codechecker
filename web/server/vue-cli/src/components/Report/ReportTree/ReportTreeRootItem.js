import { DetectionStatus, Severity } from "@cc/report-server-types";

import ReportTreeKind from "./ReportTreeKind";

const rootItems = [
  {
    id: "critical",
    name: "Critical",
    kind: ReportTreeKind.SEVERITY_LEVEL,
    severity: Severity.CRITICAL,
    children: []
  },
  {
    id: "high",
    name: "High",
    kind: ReportTreeKind.SEVERITY_LEVEL,
    severity: Severity.HIGH,
    children: []
  },
  {
    id: "medium",
    name: "Medium",
    kind: ReportTreeKind.SEVERITY_LEVEL,
    severity: Severity.MEDIUM,
    children: []
  },
  {
    id: "low",
    name: "Low",
    kind: ReportTreeKind.SEVERITY_LEVEL,
    severity: Severity.LOW,
    children: []
  },
  {
    id: "style",
    name: "Style",
    kind: ReportTreeKind.SEVERITY_LEVEL,
    severity: Severity.STYLE,
    children: []
  },
  {
    id: "unspecified",
    name: "Unspecified",
    kind: ReportTreeKind.SEVERITY_LEVEL,
    severity: Severity.UNSPECIFIED,
    children: []
  },
  {
    id: "resolved",
    name: "Resolved",
    kind: ReportTreeKind.DETECTION_STATUS,
    detectionStatus: DetectionStatus.RESOLVED,
    children: []
  }
];

export default rootItems;
