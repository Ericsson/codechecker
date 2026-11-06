const { DefinePlugin } = require('webpack');
const { merge } = require('webpack-merge');
const MinimizerPlugin = require('minimizer-webpack-plugin');

const common = require('./webpack.common.js');
const helpers = require('./helpers');

module.exports = merge(common, {
  mode: 'production',
  output: {
    path: helpers.root('dist'),
    filename: '[name].[contenthash].js',
    publicPath: "/",
    // Remove the previous build output before emitting the new one.
    clean: true
  },
  optimization: {
    minimizer: [
      // esbuild is many times faster than the default Terser minifier.
      new MinimizerPlugin({
        minify: MinimizerPlugin.esbuildMinify,
        minimizerOptions: {
          // Keep in sync with the "browserslist" field of package.json, so
          // the minifier doesn't introduce syntax unsupported by those
          // browsers.
          target: 'es2020',
          logOverride: {
            // The generated Thrift API stubs contain duplicate `case 0:`
            // clauses. They are harmless and our own sources are checked for
            // this by ESLint (`no-duplicate-case`).
            'duplicate-case': 'silent'
          }
        }
      })
    ]
  },
  plugins: [
    new DefinePlugin({
      'process.env': {
        'CC_SERVER_HOST': process.env.CC_SERVER_HOST || null,
        'CC_SERVER_PORT': process.env.CC_SERVER_PORT || null
      }
    })
  ]
});
