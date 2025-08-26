const { DefinePlugin } = require('webpack');
const { merge } = require('webpack-merge');

const common = require('./webpack.common.js');

const CC_SERVICE_ENDPOINTS = [
  'Authentication',
  'Configuration',
  'CodeCheckerService',
  'Products',
  'ServerInfo'
];

const CC_THRIFT_API_HOST =
  process.env.CC_THRIFT_API_HOST || 'http://localhost';
const CC_THRIFT_API_PORT = process.env.CC_THRIFT_API_PORT || 8002;

module.exports = merge(common, {
  mode: 'development',
  output: {
    filename: '[name].[contenthash].js',
    publicPath: "/"
  },
  devtool: 'inline-source-map',
  devServer: {
    port: 8080,
    hot: true,
    historyApiFallback: {
      rewrites: [
        {
          from: new RegExp(
            "^\\/[^/]+(\\/.*\\." +
            "(js|css|png|jpe?g|gif|ico|woff2?|eot|ttf|otf))$",
            "i"
          ),
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
    proxy: {
      "/v6": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false
      },
      "/Default": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false
      },
      "/v6.61": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false
      },
      "/v6.62": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false
      },
      "/docs": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false
      },
      "/Configuration": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false
      },
      "/ServerInfo": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false
      },
      "/CodeCheckerService": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false
      }
    }
  },
  plugins: [
    new DefinePlugin({
      "process.env": {
        "CC_SERVER_HOST": JSON.stringify("localhost"),
        "CC_SERVER_PORT": JSON.stringify("8001"),
        "CC_API_VERSION": JSON.stringify("6.62")
      }
    })
  ]
});
