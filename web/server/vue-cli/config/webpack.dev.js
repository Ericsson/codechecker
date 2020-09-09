const merge = require('webpack-merge');
const { DefinePlugin } = require('webpack');

const common = require('./webpack.common.js');

const CC_SERVICE_ENDPOINTS = [
  'Authentication',
  'Configuration',
  'CodeCheckerService',
  'Products',
  'ServerInfo'
];

// Location of the Thrift API server.
const CC_THRIFT_API_HOST =
  process.env.CC_THRIFT_API_HOST || 'http://localhost';
const CC_THRIFT_API_PORT = process.env.CC_THRIFT_API_PORT || 8001;

const METADATA = merge(common.METADATA, {
  'CC_SERVER_HOST': process.env.CC_SERVER_HOST || null,
  'CC_SERVER_PORT': process.env.CC_SERVER_PORT || null
});

module.exports = merge(common, {
  mode: 'development',
  output: {
    filename: '[name].[hash].js',
    publicPath: "/"
  },
  devtool: 'inline-source-map',
  devServer: {
    port: 8080,
    hot: true,
    historyApiFallback: {
      // If the URL contains a product endpoint and we server a static file
      // we will remove the rewrite the URL and remove the product endpoint
      // from it.
      rewrites: [
        {
          from: /^\/[^\/]+(\/.*\.(js|css|png|jpe?g|gif|ico|woff2?|eot|ttf|otf))$/i,
          to: function (ctx) {
            if (ctx.match) return ctx.match[1];

            return "/index.html";
          }
        },
        {
          from: /^\/(products|login)\.html$/i,
          to: "/index.html"
        }
      ]
    },
    proxy: [{
      context: [
        ...CC_SERVICE_ENDPOINTS.map(endpoint => `**/${endpoint}`),
        "/docs/**"
      ],
      target: CC_THRIFT_API_HOST + ':' + CC_THRIFT_API_PORT,
      changeOrigin: true,
      secure: false
    }]
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
