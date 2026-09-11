function generateGradientWithAlpha(value, max, opacity) {
  const ratio = Math.min(value / max, 1);
  const red = Math.round(ratio * 220);
  const green = Math.round((1 - ratio) * 180 + 40);
  const blue  = 40;
  return "rgba(" + red + "," + green + "," + blue + "," + opacity + ")";
}

function generateGradient(value, max) {
  const ratio = Math.min(value / max, 1);
  const red = Math.round(ratio * 160);
  const green = Math.round((1 - ratio) * 130 + 20);
  const blue = 20;
  return "rgb(" + red + "," + green + "," + blue + ")";
}

export function useGradientColor() {
  const getGradientColor = (length, limit = 20) => {
    return generateGradientWithAlpha(length, limit, 1);
  };

  const getTonalGradientColor = (length, limit = 20, opacity = 0.25) => {
    return generateGradientWithAlpha(length, limit, opacity);
  };

  const getGradientTextColor = (length, limit = 20) => {
    return generateGradient(length, limit);
  };

  return { getGradientColor, getTonalGradientColor, getGradientTextColor };
}