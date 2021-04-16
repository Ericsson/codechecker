const CopyPlugin = require('copy-webpack-plugin');
const HTMLWebpackPlugin = require('html-webpack-plugin');
const { VueLoaderPlugin } = require('vue-loader');
const VuetifyLoaderPlugin = require('vuetify-loader/lib/plugin');
const { DefinePlugin } = require('webpack');

const { join } = require('path');

const codeCheckerApi = require('codechecker-api/package.json');

const helpers = require('./helpers');

const apiVersion = codeCheckerApi.version.split('.').slice(0, 2).join('.');
const METADATA = {
  'CC_SERVER_HOST': null,
  'CC_SERVER_PORT': 80,
  'CC_API_VERSION': JSON.stringify(apiVersion)
};

function sassLoaderOptions(indentedSyntax=false) {
  return {
    implementation: require('sass'),
    prependData: `@import "~@/variables.scss"` + (indentedSyntax ? '' : ';'),
    sassOptions: { indentedSyntax },
  }
}

module.exports = {
  entry: helpers.root('src', 'main.js'),
  optimization: {
    moduleIds: 'hashed',
    runtimeChunk: 'single',
     splitChunks: {
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
      },
    },
  },
  resolve: {
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
        test: /\.(js|vue)$/,
        loader: 'eslint-loader',
        exclude: [/node_modules/],
        enforce: 'pre',
        options: {
          emitWarning: true,
          configFile: './.eslintrc.js'
        }
      },
      {
        test: /\.css$/,
        use: [
          'vue-style-loader',
          'css-loader'
        ]
      },
      {
        test:/\.sass$/,
        use: [
          'vue-style-loader',
          'css-loader',
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
          'css-loader',
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
              name: '[name].[hash:7].[ext]'
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
      'process.env': {
        'CC_API_VERSION': METADATA.CC_API_VERSION
      }
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
        }
      ]
    }),
  ]
}
