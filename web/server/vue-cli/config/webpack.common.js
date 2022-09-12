const CopyPlugin = require('copy-webpack-plugin');
const HTMLWebpackPlugin = require('html-webpack-plugin');
const { VueLoaderPlugin } = require('vue-loader');
const VuetifyLoaderPlugin = require('vuetify-loader/lib/plugin');
const { DefinePlugin, ProvidePlugin } = require('webpack');
const ESLintPlugin = require('eslint-webpack-plugin');

const { join } = require('path');

const codeCheckerApi = require('codechecker-api/package.json');
const apiVersion = codeCheckerApi.version.split('.').slice(0, 2).join('.');

const helpers = require('./helpers');

function sassLoaderOptions(indentedSyntax=false) {
  return {
    implementation: require('sass'),
    additionalData: `@import "~@/variables.scss"` + (indentedSyntax ? '' : ';'),
    sassOptions: { indentedSyntax },
  }
}

function cssLoaderOptions() {
  return {
    esModule: false
  }
}

module.exports = {
  entry: helpers.root('src', 'main.js'),
  optimization: {
    moduleIds: 'deterministic',
    runtimeChunk: 'single',
    splitChunks: {
      cacheGroups: {
        defaultVendors: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
      },
    },
  },
  resolve: {
    fallback: {
      "buffer": require.resolve('buffer/'),
      "util": require.resolve('util/'),
    },
    unsafeCache: true,
    extensions: ['.js', '.vue'],
    alias: {
      '@': helpers.root('src'),
      '@cc-api': helpers.root('src', 'services', 'api'),
      '@cc/auth': join('codechecker-api', 'lib', 'codeCheckerAuthentication.js'),
      '@cc/auth-types': join('codechecker-api', 'lib', 'authentication_types.js'),
      '@cc/conf': join('codechecker-api', 'lib', 'configurationService.js'),
      '@cc/conf-types': join('codechecker-api', 'lib', 'configuration_types.js'),
      '@cc/db-access': join('codechecker-api', 'lib', 'codeCheckerDBAccess.js'),
      '@cc/prod': join('codechecker-api', 'lib', 'codeCheckerProductService.js'),
      '@cc/prod-types': join('codechecker-api', 'lib', 'products_types.js'),
      '@cc/server-info': join('codechecker-api', 'lib', 'serverInfoService.js'),
      '@cc/report-server-types': join('codechecker-api', 'lib', 'report_server_types.js'),
      '@cc/shared-types': join('codechecker-api', 'lib', 'codechecker_api_shared_types.js'),
      'thrift': join('thrift', 'lib', 'nodejs', 'lib', 'thrift', 'browser.js'),
      'Vuetify': join('vuetify', 'lib', 'components')
    }
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        loader: 'babel-loader',
        exclude: [/node_modules\/(?!vuetify)/],
        options: {
          presets: [
            ["@babel/preset-env", {
              useBuiltIns: "usage",
              corejs: 3,
            }]
          ]
        }
      },
      {
        test: /\.vue$/,
        loader: 'vue-loader'
      },
      {
        test: /\.css$/,
        use: [
          'vue-style-loader',
          {
            loader: 'css-loader',
            options: cssLoaderOptions()
          },
        ]
      },
      {
        test:/\.sass$/,
        use: [
          'vue-style-loader',
          {
            loader: 'css-loader',
            options: cssLoaderOptions()
          },
          {
            loader: 'sass-loader',
            options: sassLoaderOptions(true)
          }
        ]
      },
      {
        test:/\.scss$/,
        use: [
          'vue-style-loader',
          {
            loader: 'css-loader',
            options: cssLoaderOptions()
          },
          {
            loader: 'sass-loader',
            options: sassLoaderOptions(false)
          }
        ]
      },
      {
        test: /\.(png|jpe?g|gif)$/i,
        use: [
          {
            loader: 'file-loader',
            options: {
              esModule: false,
              name(file) {
                if (process.env.NODE_ENV === 'development') {
                  return '[path][name].[ext]';
                }

                return '[contenthash].[ext]';
              },
            }
          }
        ]
      },
      {
        test: /\.(woff2?|eot|ttf|otf)$/,
        use: [
          {
            loader: 'file-loader',
            options: {
              limit: 10000,
              name: '[name].[contenthash:7].[ext]'
            }
          }
        ]
      },
      {
        test: /\.(md)$/,
        use: [
          {
            loader: 'raw-loader'
          }
        ]
      }
    ]
  },
  plugins: [
    new DefinePlugin({
      'process.env.CC_API_VERSION': JSON.stringify(apiVersion)
    }),
    new ProvidePlugin({
      Buffer: ['buffer', 'Buffer'],
    }),
    new ESLintPlugin({
      extensions: ['js', 'vue'],
      overrideConfigFile: './.eslintrc.js'
    }),
    new VueLoaderPlugin(),
    new VuetifyLoaderPlugin(),
    new HTMLWebpackPlugin({
      showErrors: true,
      cache: true,
      title: 'CodeChecker viewer',
      favicon: helpers.root('src', 'assets', 'favicon.ico'),
      template: helpers.root('src', 'index.html')
    }),
    new CopyPlugin({
      patterns: [
        {
          from: helpers.root('src', 'assets', 'userguide', 'images'),
          to: helpers.root('dist', 'images')
        },
        {
          from: helpers.root('src', 'browsersupport.js'),
          to: helpers.root('dist')
        },
        {
          from: helpers.root('src', 'static.js'),
          to: helpers.root('dist')
        }
      ]
    }),
  ]
}
