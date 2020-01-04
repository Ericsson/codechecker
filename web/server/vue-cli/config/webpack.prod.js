const merge = require('webpack-merge');
const { DefinePlugin } = require('webpack');

const common = require('./webpack.common.js');

const METADATA = merge(common.METADATA, {
  'CC_SERVER_HOST': process.env.CC_SERVER_HOST || null,
  'CC_SERVER_PORT': process.env.CC_SERVER_PORT || null
});

module.exports = merge(common, {
  mode: 'production',
  plugins: [
    new DefinePlugin({
      'process.env': {
        'CC_SERVER_HOST': METADATA.CC_SERVER_HOST,
        'CC_SERVER_PORT': METADATA.CC_SERVER_PORT
      }
    })
  ]
});
