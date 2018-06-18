var profile = (function(){ 
  return { 
    basePath: ".", 
    releaseDir: ".",
    releaseName: "dojo-build",
    action: "release", 
    layerOptimize: "closure", 
    optimize: "closure", 
    cssOptimize: "comments", 
    mini: true, 
    stripConsole: "warn", 
    selectorEngine: "acme", 

    defaultConfig: { 
      hasCache: { 
        "dojo-built": 1, 
        "dojo-loader": 1, 
        "dom": 1, 
        "host-browser": 1, 
        "config-selectorEngine": "lite" 
      }, 
      async: 1 
    }, 

    staticHasFeatures: { 
      "config-deferredInstrumentation": 0, 
      "config-dojo-loader-catches": 0, 
      "config-tlmSiblingOfDojo": 0, 
      "dojo-amd-factory-scan": 0, 
      "dojo-combo-api": 0, 
      "dojo-config-api": 1, 
      "dojo-config-require": 0, 
      "dojo-debug-messages": 0, 
      "dojo-dom-ready-api": 1, 
      "dojo-firebug": 0, 
      "dojo-guarantee-console": 1, 
      "dojo-has-api": 1, 
      "dojo-inject-api": 1, 
      "dojo-loader": 1, 
      "dojo-log-api": 0, 
      "dojo-modulePaths": 0, 
      "dojo-moduleUrl": 0, 
      "dojo-publish-privates": 0, 
      "dojo-requirejs-api": 0, 
      "dojo-sniff": 1, 
      "dojo-sync-loader": 0, 
      "dojo-test-sniff": 0, 
      "dojo-timeout-api": 0, 
      "dojo-trace-api": 0,
      "dojo-undef-api": 0, 
      "dojo-v1x-i18n-Api": 1, 
      "dom": 1, 
      "host-browser": 1, 
      "extend-dojo": 1 
    }, 

    packages: [
      { name: 'dojo',  location: './node_modules/dojo'  },
      { name: 'dijit', location: './node_modules/dijit' },
      { name: 'dojox', location: './node_modules/dojox' }
    ],

    layers: {
      "dojox/grid/DataGrid": {
        include: [
          "dojox/grid/_View"
        ],
        customBase: 1
      },
      "dojo/dojo": {
        include: [
          "dojo/Deferred",
          "dojo/Evented",
          "dojo/NodeList-dom",
          "dojo/_base/Color",
          "dojo/_base/Deferred",
          "dojo/_base/NodeList",
          "dojo/_base/array",
          "dojo/_base/config",
          "dojo/_base/connect",
          "dojo/_base/declare",
          "dojo/_base/event",
          "dojo/_base/fx",
          "dojo/_base/html",
          "dojo/_base/json",
          "dojo/_base/kernel",
          "dojo/_base/lang",
          "dojo/_base/loader",
          "dojo/_base/sniff",
          "dojo/_base/unload",
          "dojo/_base/window",
          "dojo/_base/xhr",
          "dojo/aspect",
          "dojo/dom",
          "dojo/dom-attr",
          "dojo/dom-class",
          "dojo/dom-construct",
          "dojo/dom-form",
          "dojo/dom-geometry",
          "dojo/dom-prop",
          "dojo/dom-style",
          "dojo/domReady",
          "dojo/errors/CancelError",
          "dojo/errors/RequestError",
          "dojo/errors/RequestTimeoutError",
          "dojo/errors/create",
          "dojo/has",
          "dojo/i18n",
          "dojo/io-query",
          "dojo/json",
          "dojo/keys",
          "dojo/loadInit",
          "dojo/main",
          "dojo/mouse",
          "dojo/on",
          "dojo/promise/Promise",
          "dojo/promise/instrumentation",
          "dojo/promise/tracer",
          "dojo/query",
          "dojo/ready",
          "dojo/request",
          "dojo/request/default",
          "dojo/request/handlers",
          "dojo/request/util",
          "dojo/request/watch",
          "dojo/request/xhr",
          "dojo/selector/_loader",
          "dojo/selector/acme",
          "dojo/sniff",
          "dojo/text",
          "dojo/topic",
          "dojo/when"
        ],
        customBase: 1
      }
    }
  };
})();

