const CopyPlugin = require("copy-webpack-plugin");
const HTMLWebpackPlugin = require("html-webpack-plugin");
const { VueLoaderPlugin } = require("vue-loader");
const { DefinePlugin, ProvidePlugin } = require("webpack");
const ESLintPlugin = require("eslint-webpack-plugin");

const { join } = require("path");
const helpers = require("./helpers");

// Generated Thrift API JavaScript stubs
const apiDir = helpers.root("..", "..", "..", "codechecker_api");
const apiJsDir = join(apiDir, "js");
const apiVersion = require(join(apiDir, "api_version.json")).api_version;

function sassLoaderOptions(indentedSyntax=false) {
  return {
    api: "modern-compiler",
    implementation: require("sass"),
    additionalData: `@use "@/variables.scss"` + (indentedSyntax ? "" : ";"),
    sassOptions: {
      indentedSyntax,
      quietDeps: true,
      silenceDeprecations: [
        "legacy-js-api",
        "import",
        "if",
        "mixed-decls",
        "color-functions",
        "global-builtin"
      ],
    },
  };
}

function cssLoaderOptions() {
  return {
    esModule: false
  };
}

module.exports = {
  entry: helpers.root("src", "main.js"),
  optimization: {
    moduleIds: "deterministic",
    runtimeChunk: "single",
    splitChunks: {
      cacheGroups: {
        defaultVendors: {
          test: /[\\/]node_modules[\\/]/,
          name: "vendors",
          chunks: "all",
          priority: 10
        },
        vuetify: {
          test: /[\\/]node_modules[\\/]vuetify[\\/]/,
          name: "vuetify",
          chunks: "all",
          priority: 20
        }
      },
    },
  },
  resolve: {
    fallback: {
      "buffer": require.resolve("buffer/"),
      "util": require.resolve("util/"),
    },
    unsafeCache: false,
    extensions: [ ".js", ".vue" ],
    // Let the external Thrift API stubs (in `codechecker_api/js`) resolve
    // their bare `require("thrift")` / `require("node-int64")` against this
    // project's node_modules.
    modules: [ helpers.root("node_modules"), "node_modules" ],
    alias: {
      "@": helpers.root("src"),
      "@statistics": helpers.root("src", "components", "Statistics"),
      "@cc-api": helpers.root("src", "services", "api"),
      "@cc/auth": join(apiJsDir, "codeCheckerAuthentication.js"),
      "@cc/auth-types": join(apiJsDir, "authentication_types.js"),
      "@cc/conf": join(apiJsDir, "configurationService.js"),
      "@cc/conf-types": join(apiJsDir, "configuration_types.js"),
      "@cc/db-access": join(apiJsDir, "codeCheckerDBAccess.js"),
      "@cc/prod": join(apiJsDir, "codeCheckerProductService.js"),
      "@cc/prod-types": join(apiJsDir, "products_types.js"),
      "@cc/server-info": join(apiJsDir, "serverInfoService.js"),
      "@cc/report-server-types": join(apiJsDir, "report_server_types.js"),
      "@cc/shared-types": join(apiJsDir, "shared_types.js"),
      "thrift": join("thrift", "lib", "nodejs", "lib", "thrift", "browser.js"),
      "Vuetify": join("vuetify", "lib", "components"),
    }
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        loader: "babel-loader",
        // The Thrift API stubs (in `codechecker_api/js`) are plain CommonJS.
        // Exclude them like node_modules so babel doesn't turn them into ES
        // modules and break their `module.exports`.
        exclude: [
          /node_modules\/(?!vuetify)/,
          /[\\/]codechecker_api[\\/]js[\\/]/
        ],
        options: {
          presets: [
            [ "@babel/preset-env", {
              useBuiltIns: "usage",
              corejs: 3,
            } ]
          ]
        }
      },
      {
        test: /\.vue$/,
        loader: "vue-loader",
        options: {}
      },
      {
        test: /\.css$/,
        use: [
          "vue-style-loader",
          {
            loader: "css-loader",
            options: cssLoaderOptions()
          },
        ]
      },
      {
        test:/\.sass$/,
        use: [
          "vue-style-loader",
          {
            loader: "css-loader",
            options: cssLoaderOptions()
          },
          {
            loader: "sass-loader",
            options: sassLoaderOptions(true)
          }
        ]
      },
      {
        test:/\.scss$/,
        use: [
          "vue-style-loader",
          {
            loader: "css-loader",
            options: cssLoaderOptions()
          },
          {
            loader: "sass-loader",
            options: sassLoaderOptions(false)
          }
        ]
      },
      {
        test: /\.(png|jpe?g|gif)$/i,
        use: [
          {
            loader: "file-loader",
            options: {
              esModule: false,
              name() {
                if (process.env.NODE_ENV === "development") {
                  return "[path][name].[ext]";
                }

                return "[contenthash].[ext]";
              },
            }
          }
        ]
      },
      {
        test: /\.(woff2?|eot|ttf|otf)$/,
        use: [
          {
            loader: "file-loader",
            options: {
              limit: 10000,
              name: "[name].[contenthash:7].[ext]"
            }
          }
        ]
      },
      {
        test: /\.(md)$/,
        use: [
          {
            loader: "raw-loader"
          }
        ]
      }
    ]
  },
  plugins: [
    new DefinePlugin({
      "process.env.CC_API_VERSION": JSON.stringify(apiVersion),
      __VUE_OPTIONS_API__: true,
      __VUE_PROD_DEVTOOLS__: false,
      __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false
    }),
    new ProvidePlugin({
      Buffer: [ "buffer", "Buffer" ],
    }),
    new ESLintPlugin({
      extensions: [ "js", "vue" ]//,
      //overrideConfigFile: "./.eslintrc.js"
    }),
    new VueLoaderPlugin(),
    new HTMLWebpackPlugin({
      showErrors: true,
      cache: true,
      title: "CodeChecker viewer",
      favicon: helpers.root("src", "assets", "favicon.ico"),
      template: helpers.root("src", "index.html")
    }),
    new CopyPlugin({
      patterns: [
        {
          from: helpers.root("src", "assets", "userguide", "images"),
          to: helpers.root("dist", "images")
        },
        {
          from: helpers.root("src", "browsersupport.js"),
          to: helpers.root("dist")
        },
        {
          from: helpers.root("src", "static.js"),
          to: helpers.root("dist")
        }
      ]
    }),
  ],
  stats: {
    warningsFilter: [
      /sass-loader/i,
      /Deprecation Warning/i,
      /SassDeprecationWarning/i,
      /The Sass if\(\) syntax is deprecated/i,
      /vuetify.*sass/i,
      /Module Warning.*sass-loader/i
    ]
  },
  cache: {
    type: "filesystem",
    buildDependencies: {
      config: [ __filename ]
    }
  },
  snapshot: {
    managedPaths: [ helpers.root("node_modules") ]
  }
};
