const HTMLWebpackPlugin = require('html-webpack-plugin');
const { VueLoaderPlugin } = require('vue-loader');
const VuetifyLoaderPlugin = require('vuetify-loader/lib/plugin');
const { DefinePlugin } = require('webpack');

const { join } = require('path');

const helpers = require('./helpers');

const METADATA = {
  'CC_SERVER_HOST': null,
  'CC_SERVER_PORT': 80,
  'CC_API_VERSION': JSON.stringify('6.24')
};

const cc_api_dir = helpers.root('src', 'codechecker_api');

module.exports = {
  entry: helpers.root('src', 'main.js'),
  output: {
    path: helpers.root('dist'),
    filename: 'app.bundler.js'
  },
  resolve: {
    extensions: ['.js', '.vue'],
    alias: {
      '@': helpers.root('src'),
      '@cc-api': helpers.root('src', 'services', 'api'),
      '@cc/auth': join(cc_api_dir, 'codeCheckerAuthentication.js'),
      '@cc/auth-types': join(cc_api_dir, 'authentication_types.js'),
      '@cc/conf': join(cc_api_dir, 'configurationService.js'),
      '@cc/conf-types': join(cc_api_dir, 'configuration_types.js'),
      '@cc/db-access': join(cc_api_dir, 'codeCheckerDBAccess.js'),
      '@cc/prod': join(cc_api_dir, 'codeCheckerProductService.js'),
      '@cc/prod-types': join(cc_api_dir, 'products_types.js'),
      '@cc/report-server-types': join(cc_api_dir, 'report_server_types.js'),
      '@cc/shared-types': join(cc_api_dir, 'codechecker_api_shared_types.js'),
      'thrift': join('thrift', 'lib', 'nodejs', 'lib', 'thrift', 'browser.js'),
      'Vuetify': join('vuetify', 'lib', 'components')
    }
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        loader: 'babel-loader',
        exclude: [/node_modules/, cc_api_dir],
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
        exclude: [/node_modules/, cc_api_dir],
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
        test:/\.s(c|a)ss$/,
        use: [
          'vue-style-loader',
          'css-loader',
          {
            loader: 'sass-loader',
            options: {
              implementation: require('sass'),
              sassOptions: {
                fiber: require('fibers')
              }
            }
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
    })
  ]
}
