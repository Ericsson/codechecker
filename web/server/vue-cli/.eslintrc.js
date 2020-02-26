module.exports = {
  root: true,
  env: {
    node: true
  },
  extends: [
    "plugin:vue/recommended",
    "eslint:recommended"
  ],
  rules: {
    "array-bracket-spacing": ["error", "always"],
    "arrow-parens": ["error", "as-needed"],
    "max-len": ["error", { "code": 80 }],
    "no-console": process.env.NODE_ENV === "production" ? "error" : "off",
    "no-debugger": process.env.NODE_ENV === "production" ? "error" : "off",
    "object-curly-spacing": ["error", "always"],
    "semi": ["error", "always"],
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
