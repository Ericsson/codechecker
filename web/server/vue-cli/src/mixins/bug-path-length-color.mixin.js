function generateRedGreenGradientColor(value, max, opacity) {
  var red   = (255 * value) / max;
  var green = (255 * (max - value)) / max;
  var blue  = 0;
  return "rgba(" + parseInt(red) + "," + parseInt(green) + "," + blue
    + "," + opacity + ")";
}

export default {
  methods: {
    getBugPathLenColor (length, limit) {
      // This value says that bug path length with this value and above are
      // difficult to understand. The background color of these bug path
      // lengths will be red.
      if (limit === undefined) {
        limit = 20;
      }

      return generateRedGreenGradientColor(length, limit, 0.5);
    },
  }
};
