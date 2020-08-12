const merge = require('webpack-merge');
const { DefinePlugin } = require('webpack');

const common = require('./webpack.common.js');
const helpers = require('./helpers');

const METADATA = merge(common.METADATA, {
  'CC_SERVER_HOST': process.env.CC_SERVER_HOST || null,
  'CC_SERVER_PORT': process.env.CC_SERVER_PORT || null
});

module.exports = merge(common, {
  mode: 'production',
  output: {
    path: helpers.root('dist'),
    filename: '[name].[contenthash].js',
    publicPath: "/"
  },
  plugins: [
    new DefinePlugin({
      'process.env': {
        'CC_SERVER_HOST': METADATA.CC_SERVER_HOST,
        'CC_SERVER_PORT': METADATA.CC_SERVER_PORT
      }
    })
  ]
});
