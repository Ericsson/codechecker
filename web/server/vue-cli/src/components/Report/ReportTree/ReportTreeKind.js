export default Object.freeze({
  SEVERITY_LEVEL: 0,
  DETECTION_STATUS: 1,
  REPORT: 2,
  REPORT_STEPS: 3,
  BUG: 4,
  MACRO_EXPANSION: 5,
  MACRO_EXPANSION_ITEM: 6,
  NOTE: 7,
  NOTE_ITEM: 8,

  getId(kind, report, index) {
    switch (kind) {
    case this.REPORT:
      return report.reportId.toString();

    case this.REPORT_STEPS:
    case this.MACRO_EXPANSION_ITEM:
    case this.NOTE_ITEM:
      return `${report.reportId}_${kind}_${index}`;

    case this.BUG:
    case this.MACRO_EXPANSION:
    case this.NOTE:
      return `${report.reportId}_${kind}`;

    default:
      console.warn("No id for the following report tree kind: ", kind);
      return null;
    }
  }
});
