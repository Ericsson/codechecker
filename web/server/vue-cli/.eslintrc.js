module.exports = {
  root: true,
  env: {
    node: true,
    jest: true
  },
  extends: [
    "plugin:vue/recommended",
    "eslint:recommended"
  ],
  rules: {
    "array-bracket-spacing": ["error", "always"],
    "arrow-parens": ["error", "as-needed"],
    "indent": ["error", 2],
    "keyword-spacing": ["error"],
    "max-len": ["error", { "code": 80 }],
    "no-console": process.env.NODE_ENV === "production"
      ? [ "error", { "allow": ["warn"] } ]
      : "off",
    "no-debugger": process.env.NODE_ENV === "production" ? "error" : "off",
    "no-duplicate-imports": ["error", { "includeExports": true }],
    "object-curly-spacing": ["error", "always"],
    "prefer-const": ["error"],
    "semi": ["error", "always"],
    "sort-imports": ["error", { "ignoreDeclarationSort": true }],
    "vue/max-attributes-per-line": ["error", {
      "singleline": 20,
      "multiline": {
        "max": 1,
        "allowFirstLine": false
      }
    }],
    "quotes": ["error", "double", {
      "avoidEscape": true
    }]
  },
  parserOptions: {
    parser: "babel-eslint",
    sourceType: "module"
  }
}
