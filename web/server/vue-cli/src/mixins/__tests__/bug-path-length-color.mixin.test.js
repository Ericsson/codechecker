import { BugPathLengthColorMixin } from "@/mixins";

const getBugPathLenColor =
  BugPathLengthColorMixin.methods.getBugPathLenColor;

describe("Get bug path length color", () => {
  test("Get bug path length color for min and max values", () => {
    expect(getBugPathLenColor(0)).toEqual("rgba(0,255,0,0.5)");
    expect(getBugPathLenColor(20)).toEqual("rgba(255,0,0,0.5)");
    expect(getBugPathLenColor(20, 20)).toEqual("rgba(255,0,0,0.5)");
  });
});
