import { DetectionStatusMixin } from "@/mixins";
import { DetectionStatus } from "@cc/report-server-types";

const toString =
  DetectionStatusMixin.methods.detectionStatusFromCodeToString;
const fromString =
  DetectionStatusMixin.methods.detectionStatusFromStringToCode;

describe("Convert detection status", () => {
  test("Convert existing detection statuses to string", () => {
    expect(toString(DetectionStatus.NEW)).toEqual("New");
    expect(toString(DetectionStatus.RESOLVED)).toEqual("Resolved");
    expect(toString(DetectionStatus.UNRESOLVED)).toEqual("Unresolved");
    expect(toString(DetectionStatus.REOPENED)).toEqual("Reopened");
    expect(toString(DetectionStatus.OFF)).toEqual("Off");
    expect(toString(DetectionStatus.UNAVAILABLE)).toEqual("Unavailable");
  });

  test("Convert non existing detection statuses to string", () => {
    expect(toString(-1)).toEqual("");
    expect(toString(null)).toEqual("");
  });

  test("Convert string to detection status", () => {
    expect(fromString("New")).toEqual(DetectionStatus.NEW);
    expect(fromString("ResOlved")).toEqual(DetectionStatus.RESOLVED);
    expect(fromString("UNRESOLVED")).toEqual(DetectionStatus.UNRESOLVED);
    expect(fromString("Reopened")).toEqual(DetectionStatus.REOPENED);
    expect(fromString("off")).toEqual(DetectionStatus.OFF);
    expect(fromString("Unavailable")).toEqual(DetectionStatus.UNAVAILABLE);
  });

  test("Convert string to non existing detection status", () => {
    expect(fromString("")).toEqual(-1);
    expect(fromString("dummy")).toEqual(-1);
  });
});
