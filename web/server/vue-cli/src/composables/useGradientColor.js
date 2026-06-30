function generateRedGreenGradientColor(value, max, opacity) {
  const ratio = Math.min(value / max, 1);
  var red = Math.round(ratio * 220);
  var green = Math.round((1 - ratio) * 180 + 40);
  var blue  = 40;
  return "rgba(" + parseInt(red) + "," + parseInt(green) + "," + blue
    + "," + opacity + ")";
}

export function useGradientColor() {
  const getGradientColor = (length, limit = 20) => {
    return generateRedGreenGradientColor(length, limit, 1);
  };

  return { getGradientColor };
}