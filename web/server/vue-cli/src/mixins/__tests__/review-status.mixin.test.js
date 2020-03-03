import { ReviewStatusMixin } from "@/mixins";
import { ReviewStatus } from "@cc/report-server-types";

const toString =
  ReviewStatusMixin.methods.reviewStatusFromCodeToString;
const fromString =
  ReviewStatusMixin.methods.reviewStatusFromStringToCode;

describe("Convert review status", () => {
  test("Convert existing review statuses to string", () => {
    expect(toString(ReviewStatus.UNREVIEWED)).toEqual("Unreviewed");
    expect(toString(ReviewStatus.CONFIRMED)).toEqual("Confirmed bug");
    expect(toString(ReviewStatus.FALSE_POSITIVE)).toEqual("False positive");
    expect(toString(ReviewStatus.INTENTIONAL)).toEqual("Intentional");
  });

  test("Convert non existing review statuses to string", () => {
    expect(toString(-1)).toEqual("");
    expect(toString(null)).toEqual("");
  });

  test("Convert string to review status", () => {
    expect(fromString("Unreviewed")).toEqual(ReviewStatus.UNREVIEWED);
    expect(fromString("Confirmed bug")).toEqual(ReviewStatus.CONFIRMED);
    expect(fromString("false positive")).toEqual(ReviewStatus.FALSE_POSITIVE);
    expect(fromString("intentional")).toEqual(ReviewStatus.INTENTIONAL);
  });

  test("Convert non existing review statuses to string", () => {
    expect(fromString("")).toEqual(-1);
    expect(fromString("dummy")).toEqual(-1);
  });
});
