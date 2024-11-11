import { SeverityMixin } from "@/mixins";
import { Severity } from "@cc/report-server-types";

const toString =
  SeverityMixin.methods.severityFromCodeToString;
const fromString =
  SeverityMixin.methods.severityFromStringToCode;

describe("Convert severity", () => {
  test("Convert existing severity value to string", () => {
    expect(toString(Severity.UNSPECIFIED)).toEqual("Unspecified");
    expect(toString(Severity.STYLE)).toEqual("Style");
    expect(toString(Severity.LOW)).toEqual("Low");
    expect(toString(Severity.MEDIUM)).toEqual("Medium");
    expect(toString(Severity.HIGH)).toEqual("High");
    expect(toString(Severity.CRITICAL)).toEqual("Critical");
  });

  test("Convert non existing severity to string", () => {
    expect(toString(-1)).toEqual("");
    expect(toString(null)).toEqual("");
  });

  test("Convert string to severity", () => {
    expect(fromString("Unspecified")).toEqual(Severity.UNSPECIFIED);
    expect(fromString("style")).toEqual(Severity.STYLE);
    expect(fromString("LOW")).toEqual(Severity.LOW);
    expect(fromString("MediUM")).toEqual(Severity.MEDIUM);
    expect(fromString("HIGH")).toEqual(Severity.HIGH);
    expect(fromString("critical")).toEqual(Severity.CRITICAL);
  });

  test("Convert string to non existing severity", () => {
    expect(fromString("")).toEqual(-1);
    expect(fromString("dummy")).toEqual(-1);
  });
});
