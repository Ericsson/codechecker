import { StrToColorMixin } from "@/mixins";

const strToColor =
  StrToColorMixin.methods.strToColor;

describe("Convert string to color", () => {
  test("Convert empty string to color", () => {
    expect(strToColor("")).toEqual("#000000");
  });

  test("Different strings converted to different colors", () => {
    expect(strToColor("x")).not.toEqual(strToColor("y"));
  });
});
