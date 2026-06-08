module.exports = {
  productionSourceMap: false,
  configureWebpack: {
    optimization: {
      splitChunks: {
        chunks: "all",
        maxSize: 244000,
      }
    }
  }
};
